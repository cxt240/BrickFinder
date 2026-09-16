from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image
import numpy as np
from sqlalchemy.orm import Session

from app.db import relative_to_data
from app.models.entities import Book
from app.models.schemas import IngestStatus
from app.repositories.book_cleanup_repository import BookCleanupRepository
from app.repositories.book_repository import BookRepository
from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.page_repository import PageRepository
from app.repositories.region_repository import RegionRepository
from app.repositories.set_repository import SetRepository
from app.services.embedding_service import EmbeddingService
from app.services.layout_service import LayoutService
from app.services.mask_service import MaskService
from app.services.ocr_service import OcrService
from app.services.pdf_service import DiscoveredPdf, PdfService
from app.services.status_service import StatusService
from app.settings.config import Config


class IngestManager:
    def __init__(
        self,
        session: Session,
        config: Config,
        pdf: PdfService | None = None,
        ocr: OcrService | None = None,
        layout: LayoutService | None = None,
        masks: MaskService | None = None,
        embeddings: EmbeddingService | None = None,
        status: StatusService | None = None,
    ) -> None:
        self.session = session
        self.config = config
        self.pdf = pdf or PdfService()
        self.ocr = ocr or OcrService()
        self.layout = layout or LayoutService()
        self.masks = masks or MaskService()
        self.embeddings = embeddings or EmbeddingService(config.embedding_model)
        self.status = status or StatusService(config.ingest_status_path)
        self.sets = SetRepository(session)
        self.books = BookRepository(session)
        self.pages = PageRepository(session)
        self.regions = RegionRepository(session)
        self.emb_repo = EmbeddingRepository(session)
        self.cleanup = BookCleanupRepository(session)

    def run(self) -> IngestStatus:
        discovered = self.pdf.discover(self.config.instructions_path)
        self.status.write(
            IngestStatus(
                state="running",
                message="Discovering instruction PDFs",
                files_total=len(discovered),
                files_done=0,
                started_at=self.status.now(),
            )
        )
        try:
            seen_hashes = self._ingest_files(discovered)
            self._mark_missing_sources(seen_hashes)
            self.session.commit()
            return self.status.update(
                state="complete",
                message=f"Indexed {len(seen_hashes)} booklet hash(es). Missing sources were left in the index.",
                finished_at=self.status.now(),
                current_file="",
                error=None,
            )
        except Exception as exc:
            self.session.rollback()
            self.status.update(
                state="error",
                error=str(exc),
                message="Ingest failed",
                finished_at=self.status.now(),
            )
            raise

    def _ingest_files(self, discovered: list[DiscoveredPdf]) -> set[str]:
        seen: set[str] = set()
        for index, item in enumerate(discovered, start=1):
            digest = self.pdf.sha256(item.absolute)
            seen.add(digest)
            self.status.update(
                current_file=item.relpath,
                files_done=index - 1,
                message=f"Hashing {item.relpath}",
                pages_done=0,
                pages_total=0,
            )
            existing = self.books.get_by_hash(digest)
            if existing and existing.ingest_status == "complete":
                existing.source_relpath = item.relpath
                existing.source_missing = False
                existing.size_bytes = item.size_bytes
                self.session.commit()
                self.status.update(files_done=index, message=f"Skipped {item.relpath} (already indexed)")
                continue
            if existing and existing.ingest_status != "complete":
                self._reset_book_media(existing)
                book = existing
                book.source_relpath = item.relpath
                book.size_bytes = item.size_bytes
                book.source_missing = False
                book.ingest_status = "in_progress"
            else:
                set_row = self.sets.get_or_create(item.set_name)
                book = self.books.create(
                    set_id=set_row.id,
                    book_number=self.books.next_book_number(set_row.id),
                    source_relpath=item.relpath,
                    content_sha256=digest,
                    size_bytes=item.size_bytes,
                )
            self.session.commit()
            self._ingest_book(book, item)
            book.ingest_status = "complete"
            book.source_missing = False
            self.session.commit()
            self.status.update(files_done=index, message=f"Finished {item.relpath}")
        return seen

    def _ingest_book(self, book: Book, item: DiscoveredPdf) -> None:
        document = self.pdf.open(item.absolute)
        try:
            total = document.page_count
            book.page_count = total
            self.session.commit()
            self.status.update(pages_total=total, pages_done=0, message=f"Rasterizing {item.relpath}")
            for page_index in range(total):
                self._ingest_page(book, document, page_index)
                if page_index % 5 == 0:
                    self.session.commit()
                self.status.update(pages_done=page_index + 1)
            self.session.commit()
        finally:
            document.close()

    def _ingest_page(self, book: Book, document, page_index: int) -> None:
        page_number = page_index + 1
        raster = self.pdf.raster_page(document, page_index, self.config.ingest_dpi)
        book_dir = self.config.media_path / "sets" / str(book.set_id) / "books" / str(book.id)
        page_dir = book_dir / "pages"
        region_dir = book_dir / "regions"
        page_dir.mkdir(parents=True, exist_ok=True)
        region_dir.mkdir(parents=True, exist_ok=True)

        raster_path = page_dir / f"{page_number:04d}.jpg"
        thumb_path = page_dir / f"{page_number:04d}_thumb.jpg"
        self._save_jpeg(raster, raster_path)
        thumb = self._thumb(raster)
        self._save_jpeg(thumb, thumb_path)
        thumb.close()

        page = self.pages.create(
            book_id=book.id,
            page_number=page_number,
            raster_path=relative_to_data(raster_path, self.config.data_path),
            thumb_path=relative_to_data(thumb_path, self.config.data_path),
            width=raster.width,
            height=raster.height,
        )
        fields = self.ocr.parse(self.pdf.page_text(document, page_index), page_number)
        self.pages.add_step(page.id, fields.step_number, fields.bag_number)

        try:
            self._write_regions(page, raster, region_dir)
        finally:
            raster.close()

    def refresh_from_rasters(self) -> IngestStatus:
        """Rebuild region crops/masks/embeddings from existing page JPEGs (no PDF raster)."""
        pages = self.pages.list_all()
        self.status.write(
            IngestStatus(
                state="running",
                message="Refreshing region index from rasters",
                files_total=1,
                files_done=0,
                pages_total=len(pages),
                pages_done=0,
                started_at=self.status.now(),
            )
        )
        try:
            for index, page in enumerate(pages, start=1):
                raster_path = self.config.data_path / page.raster_path
                if not raster_path.is_file():
                    self.status.update(pages_done=index, message=f"Missing raster for page {page.id}")
                    continue
                with Image.open(raster_path) as raster:
                    self._replace_regions(page, raster.convert("RGB"))
                if index % 8 == 0:
                    self.session.commit()
                self.status.update(
                    pages_done=index,
                    pages_total=len(pages),
                    message=f"Reindexed page {page.id}",
                )
            self.session.commit()
            return self.status.update(
                state="complete",
                message=f"Refreshed {len(pages)} page(s).",
                finished_at=self.status.now(),
                error=None,
            )
        except Exception as exc:
            self.session.rollback()
            self.status.update(
                state="error",
                error=str(exc),
                message="Region refresh failed",
                finished_at=self.status.now(),
            )
            raise

    def refresh_embeddings(self) -> IngestStatus:
        """Re-mask and re-embed existing crops (tight silhouette, no layout rewrite)."""
        regions = self.regions.list_all()
        self.status.write(
            IngestStatus(
                state="running",
                message="Refreshing embeddings",
                files_total=1,
                files_done=0,
                pages_total=len(regions),
                pages_done=0,
                started_at=self.status.now(),
            )
        )
        try:
            for index, region in enumerate(regions, start=1):
                crop_path = self.config.data_path / region.crop_path
                if not crop_path.is_file():
                    self.status.update(pages_done=index, message=f"Missing crop {region.id}")
                    continue
                with Image.open(crop_path) as crop:
                    rgb = crop.convert("RGB")
                    mask = self.masks.mask_instruction(rgb)
                    embedded = self._embed_crop(rgb, mask)
                    mask_path = self.config.data_path / region.mask_path
                    mask_path.parent.mkdir(parents=True, exist_ok=True)
                    mask.save(mask_path)
                    self.emb_repo.upsert(
                        region.id,
                        self.embeddings.model_name,
                        embedded.vector,
                        embedded.silhouette,
                    )
                if index % 40 == 0:
                    self.session.commit()
                    self.status.update(pages_done=index, pages_total=len(regions), message=f"Embedded region {region.id}")
            self.session.commit()
            return self.status.update(
                state="complete",
                message=f"Re-embedded {len(regions)} region(s).",
                finished_at=self.status.now(),
                pages_done=len(regions),
                error=None,
            )
        except Exception as exc:
            self.session.rollback()
            self.status.update(
                state="error",
                error=str(exc),
                message="Embedding refresh failed",
                finished_at=self.status.now(),
            )
            raise

    def _replace_regions(self, page, raster: Image.Image) -> None:
        for rel in self.regions.delete_for_page(page.id):
            path = self.config.data_path / rel
            if path.exists() and path.is_file():
                path.unlink()
        book = page.book
        region_dir = self.config.media_path / "sets" / str(book.set_id) / "books" / str(book.id) / "regions"
        region_dir.mkdir(parents=True, exist_ok=True)
        self._write_regions(page, raster, region_dir)

    def _write_regions(self, page, raster: Image.Image, region_dir: Path) -> None:
        for order, box in enumerate(self.layout.detect(raster)):
            crop = raster.crop((box.x, box.y, box.x + box.w, box.y + box.h))
            mask = self.masks.mask_instruction(crop)
            if float(np.asarray(mask.convert("L")).mean()) < 6:
                crop.close()
                mask.close()
                continue
            crop_file = region_dir / f"{page.page_number:04d}_{box.kind}_{order}.jpg"
            mask_file = region_dir / f"{page.page_number:04d}_{box.kind}_{order}_mask.png"
            self._save_jpeg(crop, crop_file)
            mask.save(mask_file)
            region = self.regions.create(
                page_id=page.id,
                kind=box.kind,
                bbox=(box.x, box.y, box.w, box.h),
                crop_path=relative_to_data(crop_file, self.config.data_path),
                mask_path=relative_to_data(mask_file, self.config.data_path),
            )
            embedded = self._embed_crop(crop, mask)
            self.emb_repo.upsert(
                region.id,
                self.embeddings.model_name,
                embedded.vector,
                embedded.silhouette,
            )
            crop.close()
            mask.close()

    def _embed_crop(self, crop: Image.Image, mask: Image.Image):
        tight_img, tight_mask = self.masks.tighten(crop, mask, pad=12)
        return self.embeddings.embed(tight_img, tight_mask)

    def _mark_missing_sources(self, seen_hashes: set[str]) -> None:
        for book in self.books.list_all():
            if book.content_sha256 not in seen_hashes:
                book.source_missing = True

    def _reset_book_media(self, book: Book) -> None:
        paths = self.cleanup.wipe_derived(book.id)
        self.session.commit()
        for rel in paths:
            path = self.config.data_path / rel
            if path.exists() and path.is_file():
                path.unlink()
        book_dir = self.config.media_path / "sets" / str(book.set_id) / "books" / str(book.id)
        if book_dir.exists():
            shutil.rmtree(book_dir, ignore_errors=True)

    def _thumb(self, image: Image.Image) -> Image.Image:
        width = self.config.thumb_width
        height = max(1, int(image.height * (width / max(1, image.width))))
        return image.resize((width, height), Image.Resampling.LANCZOS)

    def _save_jpeg(self, image: Image.Image, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(path, "JPEG", quality=self.config.jpeg_quality, optimize=True)

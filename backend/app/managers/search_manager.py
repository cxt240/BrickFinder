from __future__ import annotations

import json

from sqlalchemy.orm import Session, selectinload

from app.db import relative_to_data
from app.models.entities import Book, Page, Region, Set
from app.models.schemas import SearchHit, SearchResponse
from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.page_repository import PageRepository
from app.repositories.query_repository import QueryRepository
from app.services.embedding_service import EmbeddingService, cosine, unpack_f32
from app.services.image_service import ImageService
from app.services.mask_service import MaskService
from app.services.query_type_service import QueryTypeService
from app.settings.config import Config
from sqlalchemy import select


class SearchManager:
    def __init__(
        self,
        session: Session,
        config: Config,
        embeddings: EmbeddingService | None = None,
        masks: MaskService | None = None,
        gate: QueryTypeService | None = None,
        images: ImageService | None = None,
    ) -> None:
        self.session = session
        self.config = config
        self.embeddings = embeddings or EmbeddingService(config.embedding_model)
        self.masks = masks or MaskService()
        self.gate = gate or QueryTypeService()
        self.images = images or ImageService()
        self.emb_repo = EmbeddingRepository(session)
        self.pages = PageRepository(session)
        self.queries = QueryRepository(session)

    def search(self, image_bytes: bytes, filename: str, kind_override: str | None, top_k: int | None) -> SearchResponse:
        queries_dir = self.config.media_path / "queries"
        queries_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime, timezone

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        suffix = self.images.suffix_for(filename, image_bytes)
        raw_path = queries_dir / f"{stamp}{suffix}"
        raw_path.write_bytes(image_bytes)
        image = self.images.load_rgb(raw_path)
        mask = self.masks.mask_photo(image)
        mask_path = queries_dir / f"{stamp}_mask.png"
        mask.save(mask_path)

        predicted = self.gate.guess(image, mask)
        kind = kind_override if kind_override in {"loose_part", "subassembly"} else predicted
        preferred_kind = "callout" if kind == "loose_part" else "assembly"

        image, mask = self.masks.tighten(image, mask)
        embedded = self.embeddings.embed(image, mask)
        query_vec = unpack_f32(embedded.vector)
        query_sil = unpack_f32(embedded.silhouette)
        k = top_k or self.config.top_k
        hits = self._knn(preferred_kind, query_vec, query_sil, k)

        row = self.queries.create(
            image_path=relative_to_data(raw_path, self.config.data_path),
            mask_path=relative_to_data(mask_path, self.config.data_path),
            predicted_kind=predicted,
            override_kind=kind_override,
            topk_json=json.dumps([hit.model_dump() for hit in hits]),
        )
        return SearchResponse(query_id=row.id, kind=kind, results=hits)

    def _knn(self, preferred_kind: str, vector, silhouette, top_k: int) -> list[SearchHit]:
        index = self.emb_repo.load_index(["callout", "assembly"], self.embeddings.model_name)
        scored: list[tuple[float, float, Region]] = []
        boost = self.config.search_kind_boost
        for embedding, region in index:
            hist = cosine(vector, unpack_f32(embedding.vector))
            sil = cosine(silhouette, unpack_f32(embedding.silhouette))
            score = (
                self.config.search_hist_weight * hist
                + self.config.search_silhouette_weight * sil
            )
            if region.kind == preferred_kind:
                score += boost
            scored.append((score, hist, region))
        scored.sort(key=lambda item: item[0], reverse=True)

        hits_by_page: dict[int, SearchHit] = {}
        page_order: list[int] = []
        for score, _hist, region in scored:
            if region.page_id in hits_by_page:
                continue
            hit = self._hit_for(region, score)
            if hit is None:
                continue
            hits_by_page[region.page_id] = hit
            page_order.append(region.page_id)
            if len(page_order) >= top_k + 4:
                break

        self._promote_neighbors(page_order, hits_by_page)
        ordered = [hits_by_page[page_id] for page_id in page_order if page_id in hits_by_page]
        return ordered[:top_k]

    def _promote_neighbors(self, page_order: list[int], hits_by_page: dict[int, SearchHit]) -> None:
        """Keep the next/prev instruction page beside a strong visual hit."""
        if not page_order:
            return
        lead = hits_by_page[page_order[0]]
        prev_id, next_id = self.pages.neighbor_ids(lead.book_id, lead.page_number)
        insert_at = 1
        for neighbor_id in (prev_id, next_id):
            if neighbor_id is None:
                continue
            if neighbor_id in hits_by_page:
                if neighbor_id in page_order:
                    page_order.remove(neighbor_id)
                    page_order.insert(insert_at, neighbor_id)
                    insert_at += 1
                continue
            page = self.session.scalar(
                select(Page)
                .options(selectinload(Page.regions), selectinload(Page.steps), selectinload(Page.book).selectinload(Book.set))
                .where(Page.id == neighbor_id)
            )
            if page is None or not page.regions:
                continue
            region = page.regions[0]
            hit = self._hit_for(region, max(0.0, lead.score - 0.04))
            if hit is None:
                continue
            hits_by_page[neighbor_id] = hit
            page_order.insert(insert_at, neighbor_id)
            insert_at += 1

    def _hit_for(self, region: Region, score: float) -> SearchHit | None:
        page = self.session.scalar(
            select(Page)
            .options(
                selectinload(Page.steps),
                selectinload(Page.book).selectinload(Book.set),
            )
            .where(Page.id == region.page_id)
        )
        if page is None:
            return None
        step = page.steps[0] if page.steps else None
        book = page.book
        set_row: Set = book.set
        return SearchHit(
            score=round(float(score), 4),
            kind=region.kind,
            region_id=region.id,
            page_id=page.id,
            page_number=page.page_number,
            book_id=book.id,
            book_number=book.book_number,
            set_id=set_row.id,
            set_name=set_row.name,
            step_number=step.step_number if step else None,
            bag_number=step.bag_number if step else None,
            raster_path=page.raster_path,
            thumb_path=page.thumb_path,
            crop_path=region.crop_path,
        )

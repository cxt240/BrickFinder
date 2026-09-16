from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image


@dataclass(frozen=True)
class DiscoveredPdf:
    absolute: Path
    relpath: str
    set_name: str
    size_bytes: int


class PdfService:
    def discover(self, root: Path) -> list[DiscoveredPdf]:
        if not root.exists():
            return []
        found: list[DiscoveredPdf] = []
        for path in sorted(root.rglob("*.pdf")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            parent = path.parent.name or "Unknown Set"
            found.append(
                DiscoveredPdf(
                    absolute=path,
                    relpath=rel,
                    set_name=parent,
                    size_bytes=path.stat().st_size,
                )
            )
        return found

    def sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def open(self, path: Path) -> pymupdf.Document:
        return pymupdf.open(path)

    def raster_page(
        self,
        document: pymupdf.Document,
        page_index: int,
        dpi: int,
    ) -> Image.Image:
        page = document.load_page(page_index)
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        return image

    def page_text(self, document: pymupdf.Document, page_index: int) -> str:
        page = document.load_page(page_index)
        return page.get_text("text") or ""

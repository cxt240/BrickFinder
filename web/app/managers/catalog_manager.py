from __future__ import annotations

from app.managers.media import with_media
from app.services.backend_client import BackendClient


class CatalogManager:
    def __init__(self, client: BackendClient) -> None:
        self.client = client

    async def sets(self) -> list[dict]:
        return await self.client.sets()

    async def books(self, set_id: int | None) -> list[dict]:
        return await self.client.books(set_id)

    async def pages(self, book_id: int) -> list[dict]:
        rows = await self.client.pages(book_id)
        return [with_media(row, "raster_path", "thumb_path") for row in rows]

    async def page(self, page_id: int) -> dict:
        row = await self.client.page(page_id)
        view = with_media(row, "raster_path", "thumb_path")
        crops = []
        for crop in row.get("crops") or []:
            crops.append(with_media(crop, "crop_path", "mask_path"))
        view["crops"] = crops
        return view

from __future__ import annotations

from app.managers.media import with_media
from app.services.backend_client import BackendClient


class SearchManager:
    def __init__(self, client: BackendClient) -> None:
        self.client = client

    async def search(self, upload, kind: str | None, top_k: int | None) -> dict:
        payload = await self.client.search(upload, kind, top_k)
        results = [with_media(hit, "raster_path", "thumb_path", "crop_path") for hit in payload.get("results") or []]
        return {"query_id": payload.get("query_id"), "kind": payload.get("kind"), "results": results}

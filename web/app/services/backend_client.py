from __future__ import annotations

import httpx
from fastapi import UploadFile

from app.settings.config import get_config


class BackendClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or get_config().backend_url).rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0, read=180.0, write=180.0)
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> dict:
        response = await self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def ingest_status(self) -> dict:
        response = await self._client.get(f"{self.base_url}/ingest/status")
        response.raise_for_status()
        return response.json()

    async def ingest_run(self) -> dict:
        response = await self._client.post(f"{self.base_url}/ingest/run")
        response.raise_for_status()
        return response.json()

    async def search(self, upload: UploadFile, kind: str | None, top_k: int | None) -> dict:
        payload = await upload.read()
        files = {"image": (upload.filename or "query.jpg", payload, upload.content_type or "image/jpeg")}
        data: dict[str, str] = {}
        if kind:
            data["kind"] = kind
        if top_k is not None:
            data["top_k"] = str(top_k)
        response = await self._client.post(f"{self.base_url}/search", files=files, data=data)
        response.raise_for_status()
        return response.json()

    async def search_preview(self, upload: UploadFile) -> tuple[bytes, str]:
        payload = await upload.read()
        files = {"image": (upload.filename or "query.jpg", payload, upload.content_type or "image/jpeg")}
        response = await self._client.post(f"{self.base_url}/search/preview", files=files)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "image/jpeg")
        return response.content, content_type

    async def sets(self) -> list[dict]:
        response = await self._client.get(f"{self.base_url}/sets")
        response.raise_for_status()
        return response.json()

    async def books(self, set_id: int | None = None) -> list[dict]:
        params = {"set_id": set_id} if set_id is not None else None
        response = await self._client.get(f"{self.base_url}/books", params=params)
        response.raise_for_status()
        return response.json()

    async def pages(self, book_id: int) -> list[dict]:
        response = await self._client.get(f"{self.base_url}/books/{book_id}/pages")
        response.raise_for_status()
        return response.json()

    async def page(self, page_id: int) -> dict:
        response = await self._client.get(f"{self.base_url}/pages/{page_id}")
        response.raise_for_status()
        return response.json()

    async def feedback(self, body: dict) -> dict:
        response = await self._client.post(f"{self.base_url}/feedback", json=body)
        response.raise_for_status()
        return response.json()

    async def media(self, relpath: str) -> tuple[bytes, str]:
        response = await self._client.get(f"{self.base_url}/media/{relpath}")
        response.raise_for_status()
        content_type = response.headers.get("content-type", "application/octet-stream")
        return response.content, content_type

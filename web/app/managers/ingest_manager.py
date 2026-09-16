from __future__ import annotations

from app.services.backend_client import BackendClient


class IngestManager:
    def __init__(self, client: BackendClient) -> None:
        self.client = client

    async def status(self) -> dict:
        return await self.client.ingest_status()

    async def run(self) -> dict:
        return await self.client.ingest_run()

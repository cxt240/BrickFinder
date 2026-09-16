from __future__ import annotations

from app.services.backend_client import BackendClient


class FeedbackManager:
    def __init__(self, client: BackendClient) -> None:
        self.client = client

    async def record(self, body: dict) -> dict:
        return await self.client.feedback(body)

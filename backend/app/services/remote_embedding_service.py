from __future__ import annotations

import base64
import io

import httpx
from PIL import Image

from app.services.embedding_service import EmbeddedView, EmbeddingService


class RemoteEmbeddingService(EmbeddingService):
    """HTTP client for the vision sidecar. Same EmbeddingService surface as local DINO/CLIP."""

    uses_histogram = False

    def __init__(self, base_url: str, model_name: str) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=httpx.Timeout(300.0, connect=10.0, read=300.0))

    def embed(self, image: Image.Image, mask: Image.Image | None = None) -> EmbeddedView:
        return self.embed_many([(image, mask)])[0]

    def embed_many(self, items: list[tuple[Image.Image, Image.Image | None]]) -> list[EmbeddedView]:
        payload = {
            "model_name": self.model_name,
            "items": [
                {
                    "image_b64": self._jpeg_b64(image),
                    "mask_b64": self._png_b64(mask) if mask is not None else None,
                }
                for image, mask in items
            ],
        }
        response = self._client.post(f"{self.base_url}/embed", json=payload)
        response.raise_for_status()
        body = response.json()
        views = []
        for row in body.get("views", []):
            views.append(
                EmbeddedView(
                    vector=base64.b64decode(row["vector_b64"]),
                    silhouette=base64.b64decode(row["silhouette_b64"]),
                )
            )
        if len(views) != len(items):
            raise RuntimeError("vision sidecar returned a different number of embeddings")
        return views

    def _jpeg_b64(self, image: Image.Image) -> str:
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=92)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def _png_b64(self, mask: Image.Image) -> str:
        buf = io.BytesIO()
        mask.convert("L").save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

from __future__ import annotations

import io

from PIL import Image

from app.services.embedding_service import EmbeddedView, create_embedding_service


class VisionManager:
    """Local embedder process: run the named EmbeddingService (DINO/CLIP), no sqlite."""

    def embed_many(
        self,
        model_name: str,
        images: list[Image.Image],
        masks: list[Image.Image | None],
    ) -> list[EmbeddedView]:
        if len(images) != len(masks):
            raise ValueError("images and masks length mismatch")
        service = create_embedding_service(model_name)
        return service.embed_many(list(zip(images, masks)))

    def decode_image(self, payload: bytes) -> Image.Image:
        return Image.open(io.BytesIO(payload)).convert("RGB")

    def decode_mask(self, payload: bytes | None) -> Image.Image | None:
        if not payload:
            return None
        return Image.open(io.BytesIO(payload)).convert("L")

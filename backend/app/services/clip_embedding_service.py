from __future__ import annotations

import threading

import numpy as np
from PIL import Image
import torch

from app.services.embedding_service import EmbeddedView, EmbeddingService, pack_f32


class ClipEmbeddingService(EmbeddingService):
    """openai/clip-vit-base-patch32 image tower. Used to re-rank DINO candidates."""

    HF_ID = "openai/clip-vit-base-patch32"
    uses_histogram = False

    def __init__(self, model_name: str = "clip-vit-b-32") -> None:
        self.model_name = model_name
        self._lock = threading.Lock()
        self._processor = None
        self._model = None
        self._device = "cpu"

    def _ensure(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            from transformers import CLIPModel, CLIPProcessor

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._processor = CLIPProcessor.from_pretrained(self.HF_ID)
            self._model = CLIPModel.from_pretrained(self.HF_ID)
            self._model.eval()
            self._model.to(self._device)

    def embed(self, image: Image.Image, mask: Image.Image | None = None) -> EmbeddedView:
        return self.embed_many([(image, mask)])[0]

    def embed_many(self, items: list[tuple[Image.Image, Image.Image | None]]) -> list[EmbeddedView]:
        if not items:
            return []
        self._ensure()
        prepared = [self._composite(image.convert("RGB"), mask) for image, mask in items]
        silhouettes = [
            self._silhouette(mask if mask is not None else Image.new("L", image.size, 255))
            for image, mask in items
        ]
        pixel = self._processor(images=prepared, return_tensors="pt")["pixel_values"].to(self._device)
        with torch.inference_mode():
            vision = self._model.vision_model(pixel_values=pixel)
            feat = self._model.visual_projection(vision.pooler_output)
            feat = torch.nn.functional.normalize(feat, dim=1)
        vectors = feat.detach().cpu().numpy().astype(np.float32)
        return [
            EmbeddedView(vector=pack_f32(vector), silhouette=pack_f32(sil))
            for vector, sil in zip(vectors, silhouettes)
        ]

    def _composite(self, rgb: Image.Image, mask: Image.Image | None) -> Image.Image:
        if mask is None:
            return rgb
        arr = np.asarray(rgb, dtype=np.float32)
        weights = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
        weights = np.clip(weights, 0.0, 1.0)[..., None]
        paper = np.array([248.0, 248.0, 248.0], dtype=np.float32)
        out = arr * weights + paper * (1.0 - weights)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")

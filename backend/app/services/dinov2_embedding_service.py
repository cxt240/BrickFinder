from __future__ import annotations

import threading

import numpy as np
from PIL import Image

from app.services.embedding_service import EmbeddedView, EmbeddingService, pack_f32


class Dinov2EmbeddingService(EmbeddingService):
    """facebook/dinov2-small (384-d CLS). Silhouette still stored for light re-rank."""

    HF_ID = "facebook/dinov2-small"
    uses_histogram = False

    def __init__(self, model_name: str = "dinov2-small") -> None:
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
            import torch
            from transformers import AutoImageProcessor, AutoModel

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._processor = AutoImageProcessor.from_pretrained(self.HF_ID)
            self._model = AutoModel.from_pretrained(self.HF_ID)
            self._model.eval()
            self._model.to(self._device)

    def embed(self, image: Image.Image, mask: Image.Image | None = None) -> EmbeddedView:
        return self.embed_many([(image, mask)])[0]

    def embed_many(self, items: list[tuple[Image.Image, Image.Image | None]]) -> list[EmbeddedView]:
        if not items:
            return []
        self._ensure()
        import torch

        prepared: list[Image.Image] = []
        silhouettes: list[np.ndarray] = []
        for image, mask in items:
            rgb = image.convert("RGB")
            sil_src = mask if mask is not None else Image.new("L", rgb.size, 255)
            prepared.append(self._composite(rgb, mask))
            silhouettes.append(self._silhouette(sil_src))
        inputs = self._processor(images=prepared, return_tensors="pt")
        inputs = {key: value.to(self._device) for key, value in inputs.items()}
        with torch.inference_mode():
            hidden = self._model(**inputs).last_hidden_state[:, 0]
            hidden = torch.nn.functional.normalize(hidden, dim=1)
        vectors = hidden.detach().cpu().numpy().astype(np.float32)
        return [
            EmbeddedView(vector=pack_f32(vector), silhouette=pack_f32(sil))
            for vector, sil in zip(vectors, silhouettes)
        ]

    def _composite(self, rgb: Image.Image, mask: Image.Image | None) -> Image.Image:
        """Paint masked-out pixels instruction-white so the backbone sees the brick, not the table."""
        if mask is None:
            return rgb
        arr = np.asarray(rgb, dtype=np.float32)
        weights = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
        weights = np.clip(weights, 0.0, 1.0)[..., None]
        paper = np.array([248.0, 248.0, 248.0], dtype=np.float32)
        out = arr * weights + paper * (1.0 - weights)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")

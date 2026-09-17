from __future__ import annotations

import numpy as np
from PIL import Image

from app.services.embedding_service import (
    HIST_HUE_BINS,
    HIST_SAT_BINS,
    HIST_VAL_BINS,
    VECTOR_SIZE,
    EmbeddedView,
    EmbeddingService,
    pack_f32,
)


class HistogramEmbeddingService(EmbeddingService):
    """v1: 16×4×4 HSV histogram + 32×32 silhouette."""

    uses_histogram = True

    def __init__(self, model_name: str = "histogram-hsv-256") -> None:
        self.model_name = model_name

    def embed(self, image: Image.Image, mask: Image.Image | None = None) -> EmbeddedView:
        rgb = image.convert("RGB")
        hsv = np.asarray(rgb.convert("HSV"), dtype=np.float32)
        if mask is None:
            weights = np.ones(hsv.shape[:2], dtype=np.float32)
        else:
            weights = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
        vector = self._histogram(hsv, weights)
        silhouette = self._silhouette(mask if mask is not None else Image.new("L", rgb.size, 255))
        return EmbeddedView(vector=pack_f32(vector), silhouette=pack_f32(silhouette))

    def _histogram(self, hsv: np.ndarray, weights: np.ndarray) -> np.ndarray:
        hue = hsv[:, :, 0] / 255.0
        sat = hsv[:, :, 1] / 255.0
        val = hsv[:, :, 2] / 255.0
        h_idx = np.clip((hue * HIST_HUE_BINS).astype(np.int32), 0, HIST_HUE_BINS - 1)
        s_idx = np.clip((sat * HIST_SAT_BINS).astype(np.int32), 0, HIST_SAT_BINS - 1)
        v_idx = np.where(val >= 0.40, HIST_VAL_BINS - 1, 0).astype(np.int32)
        h_idx = np.where(sat < 0.18, 0, h_idx)
        flat = ((h_idx * HIST_SAT_BINS + s_idx) * HIST_VAL_BINS + v_idx).ravel()
        sat_boost = 1.0 + 0.35 * sat
        w = (weights * sat_boost).ravel()
        hist = np.bincount(flat, weights=w, minlength=VECTOR_SIZE).astype(np.float32)
        norm = np.linalg.norm(hist)
        if norm > 0:
            hist /= norm
        return hist

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


HIST_HUE_BINS = 16
HIST_SAT_BINS = 4
HIST_VAL_BINS = 4
VECTOR_SIZE = HIST_HUE_BINS * HIST_SAT_BINS * HIST_VAL_BINS
SILHOUETTE_SIZE = 32


def pack_f32(values: np.ndarray) -> bytes:
    return np.asarray(values, dtype=np.float32).tobytes()


def unpack_f32(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).copy()


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


@dataclass(frozen=True)
class EmbeddedView:
    vector: bytes
    silhouette: bytes


class EmbeddingService:
    """v1: HSV histogram + 32x32 silhouette. Replace this class to swap in CLIP."""

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
        v_idx = np.clip((val * HIST_VAL_BINS).astype(np.int32), 0, HIST_VAL_BINS - 1)
        flat = ((h_idx * HIST_SAT_BINS + s_idx) * HIST_VAL_BINS + v_idx).ravel()
        # Saturated pixels (the red wedge, printed inks) outrank table/page gray.
        sat_boost = 1.0 + 0.35 * sat
        w = (weights * sat_boost).ravel()
        hist = np.bincount(flat, weights=w, minlength=VECTOR_SIZE).astype(np.float32)
        norm = np.linalg.norm(hist)
        if norm > 0:
            hist /= norm
        return hist

    def _silhouette(self, mask: Image.Image) -> np.ndarray:
        small = mask.convert("L").resize((SILHOUETTE_SIZE, SILHOUETTE_SIZE), Image.Resampling.BILINEAR)
        arr = np.asarray(small, dtype=np.float32) / 255.0
        flat = arr.ravel()
        norm = np.linalg.norm(flat)
        if norm > 0:
            flat /= norm
        return flat

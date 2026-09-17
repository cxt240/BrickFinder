from __future__ import annotations

from abc import ABC, abstractmethod
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


def chroma_hue(vector: np.ndarray) -> np.ndarray:
    """16-d hue profile of saturated pixels; ignores gray/white paper and tiles' noisy hue."""
    arr = np.asarray(vector, dtype=np.float32).reshape(HIST_HUE_BINS, HIST_SAT_BINS, HIST_VAL_BINS)
    chroma = arr[:, 2:, :].sum(axis=(1, 2))
    norm = np.linalg.norm(chroma)
    if norm > 0:
        chroma = chroma / norm
    return chroma


def silhouette_iou(a: np.ndarray, b: np.ndarray) -> float:
    """Binary overlap of 32x32 silhouettes; cosine alone treats any filled blob as similar."""
    aa = np.asarray(a, dtype=np.float32).reshape(SILHOUETTE_SIZE, SILHOUETTE_SIZE)
    bb = np.asarray(b, dtype=np.float32).reshape(SILHOUETTE_SIZE, SILHOUETTE_SIZE)
    ta = 0.35 * float(aa.max()) if aa.size else 0.0
    tb = 0.35 * float(bb.max()) if bb.size else 0.0
    ma = aa > ta
    mb = bb > tb
    inter = float(np.logical_and(ma, mb).sum())
    union = float(np.logical_or(ma, mb).sum())
    return inter / union if union else 0.0


def sat_mass(vector: np.ndarray) -> float:
    """Share of hist energy that is not near-gray; lighting-invariant color amount."""
    arr = np.asarray(vector, dtype=np.float32).reshape(HIST_HUE_BINS, HIST_SAT_BINS, HIST_VAL_BINS)
    return float(arr[:, 1:, :].sum())


def silhouette_aspect(sil: np.ndarray) -> float:
    """Width/height of the 32x32 foreground; footer bars are extremely elongated."""
    arr = np.asarray(sil, dtype=np.float32).reshape(SILHOUETTE_SIZE, SILHOUETTE_SIZE)
    m = float(arr.max()) if arr.size else 0.0
    if m <= 0:
        return 1.0
    ys, xs = np.where(arr > 0.35 * m)
    if xs.size == 0:
        return 1.0
    bw = int(xs.max() - xs.min() + 1)
    bh = int(ys.max() - ys.min() + 1)
    return max(bw, bh) / max(1, min(bw, bh))


@dataclass(frozen=True)
class EmbeddedView:
    vector: bytes
    silhouette: bytes


class EmbeddingService(ABC):
    """Swap implementations by model_name. Histogram is v1; DINOv2 is a separate class."""

    model_name: str
    uses_histogram: bool = False

    @abstractmethod
    def embed(self, image: Image.Image, mask: Image.Image | None = None) -> EmbeddedView:
        raise NotImplementedError

    def embed_many(self, items: list[tuple[Image.Image, Image.Image | None]]) -> list[EmbeddedView]:
        return [self.embed(image, mask) for image, mask in items]

    def _silhouette(self, mask: Image.Image) -> np.ndarray:
        small = mask.convert("L").resize((SILHOUETTE_SIZE, SILHOUETTE_SIZE), Image.Resampling.BILINEAR)
        arr = np.asarray(small, dtype=np.float32) / 255.0
        flat = arr.ravel()
        norm = np.linalg.norm(flat)
        if norm > 0:
            flat /= norm
        return flat

    def rotated_silhouettes(self, mask: Image.Image, steps: int = 16) -> list[np.ndarray]:
        """Rotation-invariant silhouettes for phone photos vs isometric CGI."""
        gray = mask.convert("L")
        width, height = gray.size
        side = max(width, height)
        canvas = Image.new("L", (side, side), 0)
        canvas.paste(gray, ((side - width) // 2, (side - height) // 2))
        views = [self._silhouette(canvas)]
        for step in range(1, steps):
            rotated = canvas.rotate(step * (360.0 / steps), resample=Image.Resampling.BILINEAR, fillcolor=0)
            views.append(self._silhouette(rotated))
        return views


_SERVICES: dict[str, EmbeddingService] = {}


def create_embedding_service(model_name: str) -> EmbeddingService:
    name = (model_name or "histogram-hsv-256").strip()
    cached = _SERVICES.get(name)
    if cached is not None:
        return cached
    from app.settings.config import get_config

    config = get_config()
    remote = bool(config.vision_url) and config.brickfinder_role != "vision"
    if remote and not name.startswith("histogram"):
        from app.services.remote_embedding_service import RemoteEmbeddingService

        service: EmbeddingService = RemoteEmbeddingService(config.vision_url, name)
    elif name.startswith("clip"):
        from app.services.clip_embedding_service import ClipEmbeddingService

        service = ClipEmbeddingService(name)
    elif name.startswith("dinov2"):
        from app.services.dinov2_embedding_service import Dinov2EmbeddingService

        service = Dinov2EmbeddingService(name)
    else:
        from app.services.histogram_embedding_service import HistogramEmbeddingService

        service = HistogramEmbeddingService(name)
    _SERVICES[name] = service
    return service

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
_HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"mif1", b"msf1", b"heif"}


class ImageService:
    def suffix_for(self, filename: str, data: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix in SUPPORTED_SUFFIXES:
            return suffix
        if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in _HEIF_BRANDS:
            return ".heic"
        return suffix if suffix else ".jpg"

    def load_rgb(self, path: Path) -> Image.Image:
        with Image.open(path) as image:
            return self._rgb(image)

    def preview_jpeg(self, data: bytes, max_side: int = 1280, quality: int = 85) -> bytes:
        """Browser-safe JPEG of the primary image, with EXIF/HEIF orientation applied."""
        with Image.open(io.BytesIO(data)) as image:
            rgb = self._rgb(image)
        width, height = rgb.size
        longest = max(width, height)
        if longest > max_side:
            scale = max_side / longest
            rgb = rgb.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()

    def _rgb(self, image: Image.Image) -> Image.Image:
        oriented = ImageOps.exif_transpose(image)
        source = oriented if oriented is not None else image
        return source.convert("RGB")

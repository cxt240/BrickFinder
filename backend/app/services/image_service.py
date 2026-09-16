from __future__ import annotations

from pathlib import Path

from PIL import Image
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
            return image.convert("RGB")

from __future__ import annotations

from collections import deque

import numpy as np
from PIL import Image, ImageFilter


class MaskService:
    def mask_instruction(self, crop: Image.Image) -> Image.Image:
        rgb = np.asarray(crop.convert("RGB"), dtype=np.float32)
        height, width, _ = rgb.shape
        ph, pw = max(4, height // 18), max(4, width // 18)
        corners = np.concatenate(
            [
                rgb[0:ph, 0:pw].reshape(-1, 3),
                rgb[0:ph, -pw:].reshape(-1, 3),
                rgb[-ph:, 0:pw].reshape(-1, 3),
                rgb[-ph:, -pw:].reshape(-1, 3),
            ]
        )
        bg = np.median(corners, axis=0)
        dist = np.linalg.norm(rgb - bg, axis=2)
        near_white = np.all(rgb >= 242, axis=2)
        page_cut = max(12.0, min(28.0, float(np.percentile(dist, 18))))
        page_bg = dist < page_cut
        foreground = ~(near_white | page_bg)
        return Image.fromarray((foreground.astype(np.uint8) * 255), mode="L")

    def mask_photo(self, photo: Image.Image) -> Image.Image:
        rgb = np.asarray(photo.convert("RGB"), dtype=np.float32)
        gray = rgb.mean(axis=2)
        height, width = gray.shape
        ph, pw = max(8, height // 40), max(8, width // 40)
        corner_gray = np.concatenate(
            [
                gray[0:ph, 0:pw].ravel(),
                gray[0:ph, -pw:].ravel(),
                gray[-ph:, 0:pw].ravel(),
                gray[-ph:, -pw:].ravel(),
            ]
        )
        corner_rgb = np.concatenate(
            [
                rgb[0:ph, 0:pw].reshape(-1, 3),
                rgb[0:ph, -pw:].reshape(-1, 3),
                rgb[-ph:, 0:pw].reshape(-1, 3),
                rgb[-ph:, -pw:].reshape(-1, 3),
            ]
        )
        corner_lum = float(np.median(corner_gray))
        bg = np.median(corner_rgb, axis=0)
        dist = np.linalg.norm(rgb - bg, axis=2)
        sat = rgb.max(axis=2) - rgb.min(axis=2)
        if corner_lum < 95:
            lum_cut = max(48.0, float(np.percentile(gray, 70)))
            foreground = (gray > lum_cut) | ((sat > 38) & (gray > 32))
        else:
            threshold = max(28.0, float(np.percentile(dist, 58)))
            foreground = dist > threshold
        foreground[:6, :] = False
        foreground[-6:, :] = False
        foreground[:, :6] = False
        foreground[:, -6:] = False
        mask = Image.fromarray((foreground.astype(np.uint8) * 255), mode="L")
        mask = mask.filter(ImageFilter.MedianFilter(size=7))
        arr = np.asarray(mask) > 127
        arr = self._keep_primary_object(arr)
        closed = Image.fromarray((arr.astype(np.uint8) * 255), mode="L")
        closed = closed.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
        return closed

    def tighten(self, image: Image.Image, mask: Image.Image, pad: int = 16) -> tuple[Image.Image, Image.Image]:
        arr = np.asarray(mask.convert("L")) > 127
        ys, xs = np.where(arr)
        if xs.size == 0:
            return image, mask
        x0 = max(0, int(xs.min()) - pad)
        y0 = max(0, int(ys.min()) - pad)
        x1 = min(image.size[0], int(xs.max()) + pad + 1)
        y1 = min(image.size[1], int(ys.max()) + pad + 1)
        return image.crop((x0, y0, x1, y1)), mask.crop((x0, y0, x1, y1))

    def _keep_primary_object(self, foreground: np.ndarray) -> np.ndarray:
        height, width = foreground.shape
        grid_w, grid_h = 64, 48
        small = np.asarray(
            Image.fromarray((foreground.astype(np.uint8) * 255), mode="L").resize(
                (grid_w, grid_h), Image.Resampling.BILINEAR
            )
        ) > 90
        if not small.any():
            return foreground
        ys, xs = np.where(small)
        cy, cx = (grid_h - 1) / 2.0, (grid_w - 1) / 2.0
        best_score = -1.0
        seed = (int(ys[0]), int(xs[0]))
        for y, x in zip(ys.tolist(), xs.tolist()):
            central = 1.0 - 0.7 * float(np.hypot((y - cy) / grid_h, (x - cx) / grid_w))
            border = y < 2 or x < 2 or y >= grid_h - 2 or x >= grid_w - 2
            score = max(0.05, central) * (0.2 if border else 1.0)
            if score > best_score:
                best_score = score
                seed = (y, x)
        seen = np.zeros_like(small, dtype=bool)
        queue: deque[tuple[int, int]] = deque([seed])
        seen[seed] = True
        while queue:
            y, x = queue.popleft()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < grid_h and 0 <= nx < grid_w and small[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        primary = np.asarray(
            Image.fromarray((seen.astype(np.uint8) * 255), mode="L").resize(
                (width, height), Image.Resampling.NEAREST
            )
        ) > 127
        primary &= foreground
        if float(primary.mean()) < 0.002:
            return foreground
        return primary

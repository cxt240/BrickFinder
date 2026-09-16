from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class RegionBox:
    kind: str
    x: int
    y: int
    w: int
    h: int


class LayoutService:
    """Heuristic LEGO instruction split: callouts on the left, assembly on the right.

    Also emits filled white panels (part labels / mini-steps) and 2x2 tiles of large
    regions so a small printed label can match without the rest of the hull.
    """

    def detect(self, image: Image.Image) -> list[RegionBox]:
        rgb = np.asarray(image.convert("RGB"))
        height, width, _ = rgb.shape
        ink = self._ink_mask(rgb)

        split = int(width * 0.34)
        left = self._bbox(ink[:, :split])
        right = self._bbox(ink[:, split:])

        boxes: list[RegionBox] = []
        if right is None:
            right = (split, 0, max(1, width - split), height)
        else:
            rx, ry, rw, rh = right
            right = (rx + split, ry, rw, rh)
        assembly = RegionBox("assembly", *self._pad(right, width, height))
        boxes.append(assembly)

        if left is None:
            left = (0, 0, max(1, split), height)
        callout = RegionBox("callout", *self._pad(left, width, height))
        boxes.append(callout)

        for panel in self._white_panels(rgb, width, height):
            if self._iou(panel, callout) > 0.82 or self._iou(panel, assembly) > 0.82:
                continue
            boxes.append(panel)

        extras: list[RegionBox] = []
        page_area = width * height
        for box in list(boxes):
            if box.w * box.h < 0.12 * page_area:
                continue
            extras.extend(self._subtiles(box, width, height))
        boxes.extend(extras)
        return boxes

    def _white_panels(self, rgb: np.ndarray, width: int, height: int) -> list[RegionBox]:
        white = np.all(rgb >= 248, axis=2)
        grid_w = 120
        grid_h = max(1, int(round(120 * height / max(1, width))))
        small = np.asarray(
            Image.fromarray((white.astype(np.uint8) * 255), mode="L").resize(
                (grid_w, grid_h), Image.Resampling.BILINEAR
            )
        ) > 200
        labels = self._components(small)
        scale_x = width / grid_w
        scale_y = height / grid_h
        page_area = width * height
        panels: list[RegionBox] = []
        for lab in range(1, int(labels.max()) + 1):
            ys, xs = np.where(labels == lab)
            if xs.size == 0:
                continue
            x0, x1 = int(xs.min()), int(xs.max())
            y0, y1 = int(ys.min()), int(ys.max())
            bw = max(1, x1 - x0 + 1)
            bh = max(1, y1 - y0 + 1)
            fill = xs.size / (bw * bh)
            if fill < 0.4:
                continue
            px = int(x0 * scale_x)
            py = int(y0 * scale_y)
            pw = max(1, int(bw * scale_x))
            ph = max(1, int(bh * scale_y))
            area = pw * ph
            if area < 0.01 * page_area or area > 0.48 * page_area:
                continue
            aspect = pw / max(1, ph)
            if aspect > 6 or aspect < 0.18:
                continue
            panels.append(RegionBox("callout", *self._pad((px, py, pw, ph), width, height, margin=4)))
        return panels

    def _subtiles(self, box: RegionBox, width: int, height: int) -> list[RegionBox]:
        overlap = 0.18
        tiles: list[RegionBox] = []
        tile_w = max(1, int(box.w / 2 * (1 + overlap)))
        tile_h = max(1, int(box.h / 2 * (1 + overlap)))
        xs = [box.x, box.x + max(0, box.w - tile_w)]
        ys = [box.y, box.y + max(0, box.h - tile_h)]
        for y in ys:
            for x in xs:
                x0 = max(0, x)
                y0 = max(0, y)
                w = min(tile_w, width - x0)
                h = min(tile_h, height - y0)
                if w < 24 or h < 24:
                    continue
                tiles.append(RegionBox(box.kind, x0, y0, w, h))
        return tiles

    def _ink_mask(self, rgb: np.ndarray) -> np.ndarray:
        # Near-white paper is background; gray instruction boards still count as ink
        # until MaskService separates page gray from drawings.
        return np.any(rgb < 245, axis=2)

    def _bbox(self, mask: np.ndarray) -> tuple[int, int, int, int] | None:
        ys, xs = np.where(mask)
        if xs.size == 0:
            return None
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        return x0, y0, max(1, x1 - x0 + 1), max(1, y1 - y0 + 1)

    def _pad(
        self,
        box: tuple[int, int, int, int],
        width: int,
        height: int,
        margin: int = 8,
    ) -> tuple[int, int, int, int]:
        x, y, w, h = box
        x0 = max(0, x - margin)
        y0 = max(0, y - margin)
        x1 = min(width, x + w + margin)
        y1 = min(height, y + h + margin)
        return x0, y0, max(1, x1 - x0), max(1, y1 - y0)

    def _iou(self, a: RegionBox, b: RegionBox) -> float:
        ax1, ay1 = a.x + a.w, a.y + a.h
        bx1, by1 = b.x + b.w, b.y + b.h
        ix0, iy0 = max(a.x, b.x), max(a.y, b.y)
        ix1, iy1 = min(ax1, bx1), min(ay1, by1)
        inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
        union = a.w * a.h + b.w * b.h - inter
        return inter / union if union else 0.0

    def _components(self, binary: np.ndarray) -> np.ndarray:
        height, width = binary.shape
        labels = np.zeros(binary.shape, dtype=np.int32)
        current = 0
        for y in range(height):
            for x in range(width):
                if not binary[y, x] or labels[y, x]:
                    continue
                current += 1
                queue: deque[tuple[int, int]] = deque([(y, x)])
                labels[y, x] = current
                while queue:
                    cy, cx = queue.popleft()
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                        if 0 <= ny < height and 0 <= nx < width and binary[ny, nx] and not labels[ny, nx]:
                            labels[ny, nx] = current
                            queue.append((ny, nx))
        return labels

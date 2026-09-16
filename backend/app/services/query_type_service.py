from __future__ import annotations

import numpy as np
from PIL import Image


class QueryTypeService:
    def guess(self, image: Image.Image, mask: Image.Image) -> str:
        arr = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
        foreground = arr > 0.5
        density = float(foreground.mean()) if foreground.size else 0.0
        if not foreground.any():
            return "subassembly"
        ys, xs = np.where(foreground)
        bw = int(xs.max() - xs.min() + 1)
        bh = int(ys.max() - ys.min() + 1)
        img_w, img_h = image.size
        coverage = (bw * bh) / max(1, img_w * img_h)
        aspect = bw / max(1, bh)
        # Single loose bricks are compact and don't fill the frame. Built chunks
        # (including printed-tile labels) stay subassembly even when isolated.
        compact = 0.65 <= aspect <= 1.7
        fill = density / max(coverage, 1e-6)
        if density < 0.22 and coverage < 0.32 and compact and fill > 0.35:
            return "loose_part"
        return "subassembly"

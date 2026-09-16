from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PageTextFields:
    step_number: int | None
    bag_number: int | None


class OcrService:
    """PDF text-layer extraction. Swap for a real OCR engine later."""

    _bag_re = re.compile(r"\b(?:bag|pouch)\s*(\d{1,2})\b", re.IGNORECASE)
    _step_re = re.compile(r"\b(?:step)\s*(\d{1,4})\b", re.IGNORECASE)

    def parse(self, text: str, page_number: int) -> PageTextFields:
        bag = None
        step = None
        bag_match = self._bag_re.search(text)
        if bag_match:
            bag = int(bag_match.group(1))
        step_match = self._step_re.search(text)
        if step_match:
            step = int(step_match.group(1))
        if step is None:
            numbers = [int(token) for token in re.findall(r"\b(\d{1,4})\b", text)]
            candidates = [
                n
                for n in numbers
                if n != page_number and 1 <= n <= 2500 and not (1990 <= n <= 2100)
            ]
            if candidates:
                # Instruction step numbers are usually the most prominent remaining integer.
                step = max(candidates)
        return PageTextFields(step_number=step, bag_number=bag)

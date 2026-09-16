from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.models.schemas import IngestStatus


class StatusService:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> IngestStatus:
        if not self.path.exists():
            return IngestStatus(state="idle", message="No ingest has run yet.")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return IngestStatus.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValueError):
            return IngestStatus(state="running", message="Status file is updating")

    def write(self, status: IngestStatus) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(status.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def update(self, **fields: object) -> IngestStatus:
        current = self.read()
        data = current.model_dump()
        data.update(fields)
        status = IngestStatus.model_validate(data)
        self.write(status)
        return status

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

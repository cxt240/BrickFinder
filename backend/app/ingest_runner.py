from __future__ import annotations

import threading

from app.db import init_db, session_factory
from app.managers.ingest_manager import IngestManager
from app.services.status_service import StatusService
from app.settings.config import get_config

_lock = threading.Lock()


def ingest_is_running() -> bool:
    status = StatusService(get_config().ingest_status_path).read()
    return status.state == "running"


def start_background_ingest() -> bool:
    config = get_config()
    status = StatusService(config.ingest_status_path)
    with _lock:
        if status.read().state == "running":
            return False
        status.update(
            state="running",
            message="Starting ingest",
            error=None,
            finished_at=None,
            started_at=status.now(),
            files_done=0,
            pages_done=0,
        )
        thread = threading.Thread(target=run_ingest_job, daemon=True, name="brickfinder-ingest")
        thread.start()
        return True


def run_ingest_job() -> None:
    config = get_config()
    init_db(config)
    db = session_factory()()
    try:
        IngestManager(session=db, config=config).run()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.ingest_runner import ingest_is_running, start_background_ingest
from app.models.schemas import IngestStatus
from app.services.status_service import StatusService
from app.settings.config import Config, get_config

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _config() -> Config:
    return get_config()


@router.get("/status", response_model=IngestStatus)
def ingest_status(config: Config = Depends(_config)) -> IngestStatus:
    return StatusService(config.ingest_status_path).read()


@router.post("/run", response_model=IngestStatus)
def ingest_run(config: Config = Depends(_config), db: Session = Depends(get_db)) -> IngestStatus:
    del db  # session kept for layer consistency; ingest uses its own connection
    if ingest_is_running():
        return StatusService(config.ingest_status_path).read()
    start_background_ingest()
    return StatusService(config.ingest_status_path).read()

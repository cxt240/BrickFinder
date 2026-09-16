from fastapi import APIRouter, Depends

from app.endpoints.deps import get_client
from app.managers import IngestManager
from app.services.backend_client import BackendClient

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/status")
async def ingest_status(client: BackendClient = Depends(get_client)) -> dict:
    return await IngestManager(client).status()


@router.post("/run")
async def ingest_run(client: BackendClient = Depends(get_client)) -> dict:
    return await IngestManager(client).run()

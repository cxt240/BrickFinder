from fastapi import APIRouter, Depends

from app.endpoints.deps import get_client
from app.services.backend_client import BackendClient

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(client: BackendClient = Depends(get_client)) -> dict:
    try:
        backend = await client.health()
    except Exception:
        backend = {"status": "unreachable"}
    return {"status": "ok", "backend": backend}

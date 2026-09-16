from fastapi import APIRouter, Depends

from app.endpoints.deps import get_client
from app.managers import FeedbackManager
from app.services.backend_client import BackendClient

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
async def feedback(body: dict, client: BackendClient = Depends(get_client)) -> dict:
    return await FeedbackManager(client).record(body)

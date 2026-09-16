from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
import httpx

from app.endpoints.deps import get_client
from app.services.backend_client import BackendClient

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{relpath:path}")
async def media(relpath: str, client: BackendClient = Depends(get_client)) -> Response:
    try:
        content, content_type = await client.media(relpath)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="Media not found") from exc
    return Response(content=content, media_type=content_type)

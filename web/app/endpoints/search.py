from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.endpoints.deps import get_client
from app.managers import SearchManager
from app.services.backend_client import BackendClient

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/preview")
async def preview(
    image: UploadFile = File(...),
    client: BackendClient = Depends(get_client),
) -> Response:
    body, content_type = await SearchManager(client).preview(image)
    return Response(content=body, media_type=content_type)


@router.post("")
async def search(
    image: UploadFile = File(...),
    kind: str | None = Form(default=None),
    top_k: int | None = Form(default=None),
    client: BackendClient = Depends(get_client),
) -> dict:
    return await SearchManager(client).search(image, kind, top_k)

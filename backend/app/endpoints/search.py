from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import UnidentifiedImageError
from sqlalchemy.orm import Session

from app.db import get_db
from app.managers.search_manager import SearchManager
from app.models.schemas import SearchResponse
from app.settings.config import Config, get_config

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/preview")
async def preview(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    config: Config = Depends(get_config),
) -> Response:
    payload = await image.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty image upload")
    try:
        jpeg = SearchManager(db, config).preview_jpeg(payload)
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not read that photo. Use JPEG, PNG, WebP, or HEIC.",
        ) from exc
    return Response(content=jpeg, media_type="image/jpeg")


@router.post("", response_model=SearchResponse)
async def search(
    image: UploadFile = File(...),
    kind: str | None = Form(default=None),
    top_k: int | None = Form(default=None),
    db: Session = Depends(get_db),
    config: Config = Depends(get_config),
) -> SearchResponse:
    payload = await image.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty image upload")
    manager = SearchManager(db, config)
    try:
        return manager.search(payload, image.filename or "query.jpg", kind, top_k)
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not read that photo. Use JPEG, PNG, WebP, or HEIC.",
        ) from exc

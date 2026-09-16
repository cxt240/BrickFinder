from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.db import absolute_from_data
from app.settings.config import Config, get_config

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{relpath:path}")
def media(relpath: str, config: Config = Depends(get_config)) -> FileResponse:
    try:
        path = absolute_from_data(relpath, config.data_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)

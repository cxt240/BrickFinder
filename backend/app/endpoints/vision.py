from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.managers.vision_manager import VisionManager

router = APIRouter(prefix="/embed", tags=["vision"])


class EmbedItemIn(BaseModel):
    image_b64: str
    mask_b64: str | None = None


class EmbedRequest(BaseModel):
    model_name: str = Field(min_length=1)
    items: list[EmbedItemIn]


class EmbedViewOut(BaseModel):
    vector_b64: str
    silhouette_b64: str


class EmbedResponse(BaseModel):
    model_name: str
    views: list[EmbedViewOut]


def _b64_bytes(raw: str) -> bytes:
    try:
        return base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid base64") from exc


@router.post("", response_model=EmbedResponse)
def embed(body: EmbedRequest) -> EmbedResponse:
    if not body.items:
        return EmbedResponse(model_name=body.model_name, views=[])
    manager = VisionManager()
    images = []
    masks = []
    try:
        for item in body.items:
            images.append(manager.decode_image(_b64_bytes(item.image_b64)))
            masks.append(manager.decode_mask(_b64_bytes(item.mask_b64) if item.mask_b64 else None))
        views = manager.embed_many(body.model_name, images, masks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"embed failed: {exc}") from exc
    return EmbedResponse(
        model_name=body.model_name,
        views=[
            EmbedViewOut(
                vector_b64=base64.b64encode(view.vector).decode("ascii"),
                silhouette_b64=base64.b64encode(view.silhouette).decode("ascii"),
            )
            for view in views
        ],
    )

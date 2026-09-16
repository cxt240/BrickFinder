from fastapi import APIRouter, Depends

from app.endpoints.deps import get_client
from app.managers import CatalogManager
from app.services.backend_client import BackendClient

router = APIRouter(tags=["catalog"])


@router.get("/sets")
async def sets(client: BackendClient = Depends(get_client)) -> list[dict]:
    return await CatalogManager(client).sets()


@router.get("/books")
async def books(set_id: int | None = None, client: BackendClient = Depends(get_client)) -> list[dict]:
    return await CatalogManager(client).books(set_id)


@router.get("/books/{book_id}/pages")
async def pages(book_id: int, client: BackendClient = Depends(get_client)) -> list[dict]:
    return await CatalogManager(client).pages(book_id)


@router.get("/pages/{page_id}")
async def page(page_id: int, client: BackendClient = Depends(get_client)) -> dict:
    return await CatalogManager(client).page(page_id)

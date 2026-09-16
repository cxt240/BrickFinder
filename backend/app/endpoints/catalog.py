from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.managers.catalog_manager import CatalogManager
from app.models.schemas import BookOut, PageDetail, PageOut, SetOut

router = APIRouter(tags=["catalog"])


@router.get("/sets", response_model=list[SetOut])
def list_sets(db: Session = Depends(get_db)) -> list[SetOut]:
    return CatalogManager(db).list_sets()


@router.get("/books", response_model=list[BookOut])
def list_books(set_id: int | None = None, db: Session = Depends(get_db)) -> list[BookOut]:
    return CatalogManager(db).list_books(set_id)


@router.get("/books/{book_id}/pages", response_model=list[PageOut])
def list_pages(book_id: int, db: Session = Depends(get_db)) -> list[PageOut]:
    return CatalogManager(db).list_pages(book_id)


@router.get("/pages/{page_id}", response_model=PageDetail)
def get_page(page_id: int, db: Session = Depends(get_db)) -> PageDetail:
    detail = CatalogManager(db).get_page(page_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return detail

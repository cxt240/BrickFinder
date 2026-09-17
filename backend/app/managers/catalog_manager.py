from sqlalchemy.orm import Session

from app.models.schemas import BookOut, PageDetail, PageOut, RegionCropOut, SetOut
from app.repositories.book_repository import BookRepository
from app.repositories.page_repository import PageRepository
from app.repositories.set_repository import SetRepository


class CatalogManager:
    def __init__(self, session: Session) -> None:
        self.sets = SetRepository(session)
        self.books = BookRepository(session)
        self.pages = PageRepository(session)
        self.session = session

    def list_sets(self) -> list[SetOut]:
        rows = []
        for set_row, book_count, page_count in self.sets.list_with_counts():
            rows.append(
                SetOut(
                    id=set_row.id,
                    set_num=set_row.set_num,
                    name=set_row.name,
                    book_count=book_count,
                    page_count=page_count,
                )
            )
        return rows

    def list_books(self, set_id: int | None = None) -> list[BookOut]:
        if set_id is not None:
            books = self.books.list_for_set(set_id)
        else:
            books = sorted(self.books.list_all(), key=lambda b: (b.set_id, b.book_number))
        result: list[BookOut] = []
        for book in books:
            set_row = self.sets.get(book.set_id)
            result.append(
                BookOut(
                    id=book.id,
                    set_id=book.set_id,
                    set_name=set_row.name if set_row else "",
                    book_number=book.book_number,
                    source_relpath=book.source_relpath,
                    page_count=book.page_count,
                    source_missing=book.source_missing,
                    ingest_status=book.ingest_status,
                )
            )
        return result

    def list_pages(self, book_id: int) -> list[PageOut]:
        pages = self.pages.list_for_book(book_id)
        result: list[PageOut] = []
        for page in pages:
            step = page.steps[0] if page.steps else None
            result.append(
                PageOut(
                    id=page.id,
                    book_id=page.book_id,
                    page_number=page.page_number,
                    raster_path=page.raster_path,
                    thumb_path=page.thumb_path,
                    width=page.width,
                    height=page.height,
                    step_number=step.step_number if step else None,
                    bag_number=step.bag_number if step else None,
                )
            )
        return result

    def get_page(self, page_id: int) -> PageDetail | None:
        page = self.pages.get(page_id)
        if page is None:
            return None
        book = self.books.get(page.book_id)
        set_row = self.sets.get(book.set_id) if book else None
        step = page.steps[0] if page.steps else None
        prev_page_id, next_page_id = self.pages.neighbor_ids(page.book_id, page.page_number)
        crops = [
            RegionCropOut(
                id=region.id,
                kind=region.kind,
                crop_path=region.crop_path,
                mask_path=region.mask_path,
                bbox_x=region.bbox_x,
                bbox_y=region.bbox_y,
                bbox_w=region.bbox_w,
                bbox_h=region.bbox_h,
            )
            for region in page.regions
        ]
        return PageDetail(
            id=page.id,
            book_id=page.book_id,
            page_number=page.page_number,
            raster_path=page.raster_path,
            thumb_path=page.thumb_path,
            width=page.width,
            height=page.height,
            step_number=step.step_number if step else None,
            bag_number=step.bag_number if step else None,
            set_name=set_row.name if set_row else "",
            book_number=book.book_number if book else 0,
            crops=crops,
            prev_page_id=prev_page_id,
            next_page_id=next_page_id,
        )

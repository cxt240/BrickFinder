from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Page, Step


class PageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, page_id: int) -> Page | None:
        return self.session.scalar(
            select(Page)
            .options(selectinload(Page.steps), selectinload(Page.regions), selectinload(Page.book))
            .where(Page.id == page_id)
        )

    def list_all(self) -> list[Page]:
        return list(
            self.session.scalars(
                select(Page).options(selectinload(Page.book)).order_by(Page.id)
            )
        )

    def list_for_book(self, book_id: int) -> list[Page]:
        return list(
            self.session.scalars(
                select(Page)
                .options(selectinload(Page.steps))
                .where(Page.book_id == book_id)
                .order_by(Page.page_number)
            )
        )

    def neighbor_ids(self, book_id: int, page_number: int) -> tuple[int | None, int | None]:
        prev_id = self.session.scalar(
            select(Page.id)
            .where(Page.book_id == book_id, Page.page_number < page_number)
            .order_by(Page.page_number.desc())
            .limit(1)
        )
        next_id = self.session.scalar(
            select(Page.id)
            .where(Page.book_id == book_id, Page.page_number > page_number)
            .order_by(Page.page_number.asc())
            .limit(1)
        )
        return prev_id, next_id

    def create(
        self,
        *,
        book_id: int,
        page_number: int,
        raster_path: str,
        thumb_path: str,
        width: int,
        height: int,
    ) -> Page:
        row = Page(
            book_id=book_id,
            page_number=page_number,
            raster_path=raster_path,
            thumb_path=thumb_path,
            width=width,
            height=height,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def add_step(self, page_id: int, step_number: int | None, bag_number: int | None) -> Step:
        row = Step(page_id=page_id, step_number=step_number, bag_number=bag_number)
        self.session.add(row)
        self.session.flush()
        return row

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Book, Page, Set


class SetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_name(self, name: str) -> Set | None:
        return self.session.scalar(select(Set).where(Set.name == name))

    def get(self, set_id: int) -> Set | None:
        return self.session.get(Set, set_id)

    def create(self, name: str, set_num: str | None = None) -> Set:
        row = Set(name=name, set_num=set_num)
        self.session.add(row)
        self.session.flush()
        return row

    def get_or_create(self, name: str) -> Set:
        existing = self.get_by_name(name)
        if existing:
            return existing
        return self.create(name)

    def list_with_counts(self) -> list[tuple[Set, int, int]]:
        book_count = func.count(func.distinct(Book.id))
        page_count = func.count(Page.id)
        stmt = (
            select(Set, book_count, page_count)
            .outerjoin(Book, Book.set_id == Set.id)
            .outerjoin(Page, Page.book_id == Book.id)
            .group_by(Set.id)
            .order_by(Set.name)
        )
        return [(row[0], int(row[1]), int(row[2])) for row in self.session.execute(stmt)]

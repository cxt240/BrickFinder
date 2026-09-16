from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Book


class BookRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, book_id: int) -> Book | None:
        return self.session.get(Book, book_id)

    def get_by_hash(self, sha256: str) -> Book | None:
        return self.session.scalar(select(Book).where(Book.content_sha256 == sha256))

    def list_for_set(self, set_id: int) -> list[Book]:
        return list(
            self.session.scalars(
                select(Book).where(Book.set_id == set_id).order_by(Book.book_number)
            )
        )

    def list_all(self) -> list[Book]:
        return list(self.session.scalars(select(Book)))

    def next_book_number(self, set_id: int) -> int:
        current = self.session.scalar(
            select(func.max(Book.book_number)).where(Book.set_id == set_id)
        )
        return int(current or 0) + 1

    def create(
        self,
        *,
        set_id: int,
        book_number: int,
        source_relpath: str,
        content_sha256: str,
        size_bytes: int,
    ) -> Book:
        row = Book(
            set_id=set_id,
            book_number=book_number,
            source_relpath=source_relpath,
            content_sha256=content_sha256,
            size_bytes=size_bytes,
            page_count=0,
            source_missing=False,
            ingest_status="in_progress",
        )
        self.session.add(row)
        self.session.flush()
        return row

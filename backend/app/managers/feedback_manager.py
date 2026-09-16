from sqlalchemy.orm import Session

from app.models.entities import Query
from app.repositories.query_repository import QueryRepository


class FeedbackManager:
    def __init__(self, session: Session) -> None:
        self.queries = QueryRepository(session)

    def record(self, query_id: int, correct_page_id: int | None, correct_region_id: int | None) -> Query | None:
        return self.queries.record_feedback(query_id, correct_page_id, correct_region_id)

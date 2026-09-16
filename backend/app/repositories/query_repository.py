from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Query


class QueryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        image_path: str,
        mask_path: str | None,
        predicted_kind: str,
        override_kind: str | None,
        topk_json: str,
    ) -> Query:
        row = Query(
            image_path=image_path,
            mask_path=mask_path,
            predicted_kind=predicted_kind,
            override_kind=override_kind,
            topk_json=topk_json,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get(self, query_id: int) -> Query | None:
        return self.session.get(Query, query_id)

    def record_feedback(
        self,
        query_id: int,
        correct_page_id: int | None,
        correct_region_id: int | None,
    ) -> Query | None:
        row = self.get(query_id)
        if not row:
            return None
        row.correct_page_id = correct_page_id
        row.correct_region_id = correct_region_id
        self.session.flush()
        return row

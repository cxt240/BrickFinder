from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.managers.feedback_manager import FeedbackManager
from app.models.schemas import FeedbackRequest

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
def feedback(body: FeedbackRequest, db: Session = Depends(get_db)) -> dict[str, int]:
    row = FeedbackManager(db).record(body.query_id, body.correct_page_id, body.correct_region_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Query not found")
    return {"id": row.id}

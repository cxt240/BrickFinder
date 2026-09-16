from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Embedding, Region


class EmbeddingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, region_id: int, model_name: str, vector: bytes, silhouette: bytes) -> Embedding:
        existing = self.session.scalar(
            select(Embedding).where(
                Embedding.region_id == region_id,
                Embedding.model_name == model_name,
            )
        )
        if existing:
            existing.vector = vector
            existing.silhouette = silhouette
            return existing
        row = Embedding(
            region_id=region_id,
            model_name=model_name,
            vector=vector,
            silhouette=silhouette,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def load_index(self, kinds: str | list[str], model_name: str) -> list[tuple[Embedding, Region]]:
        kind_list = [kinds] if isinstance(kinds, str) else list(kinds)
        stmt = (
            select(Embedding, Region)
            .join(Region, Region.id == Embedding.region_id)
            .where(Region.kind.in_(kind_list), Embedding.model_name == model_name)
        )
        return [(row[0], row[1]) for row in self.session.execute(stmt)]

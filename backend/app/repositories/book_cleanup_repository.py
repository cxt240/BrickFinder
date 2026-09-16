from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import Embedding, Region, RegionLabel, Step


class BookCleanupRepository:
    """Deletes derived rows for a book. Does not delete the book itself."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def wipe_derived(self, book_id: int) -> list[str]:
        from app.models.entities import Page

        pages = list(self.session.scalars(select(Page).where(Page.book_id == book_id)))
        paths: list[str] = []
        page_ids = [page.id for page in pages]
        for page in pages:
            paths.extend([page.raster_path, page.thumb_path])
        if not page_ids:
            return paths
        region_ids = list(self.session.scalars(select(Region.id).where(Region.page_id.in_(page_ids))))
        for region in self.session.scalars(select(Region).where(Region.page_id.in_(page_ids))):
            paths.extend([region.crop_path, region.mask_path])
        if region_ids:
            self.session.execute(delete(Embedding).where(Embedding.region_id.in_(region_ids)))
            self.session.execute(delete(RegionLabel).where(RegionLabel.region_id.in_(region_ids)))
            self.session.execute(delete(Region).where(Region.id.in_(region_ids)))
        self.session.execute(delete(Step).where(Step.page_id.in_(page_ids)))
        self.session.execute(delete(Page).where(Page.id.in_(page_ids)))
        self.session.flush()
        return paths

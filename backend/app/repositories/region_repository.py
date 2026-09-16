from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import Embedding, Region, RegionLabel


class RegionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        page_id: int,
        kind: str,
        bbox: tuple[int, int, int, int],
        crop_path: str,
        mask_path: str,
    ) -> Region:
        x, y, w, h = bbox
        row = Region(
            page_id=page_id,
            kind=kind,
            bbox_x=x,
            bbox_y=y,
            bbox_w=w,
            bbox_h=h,
            crop_path=crop_path,
            mask_path=mask_path,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_all(self) -> list[Region]:
        return list(self.session.scalars(select(Region).order_by(Region.id)))

    def list_for_page(self, page_id: int) -> list[Region]:
        return list(self.session.scalars(select(Region).where(Region.page_id == page_id)))

    def delete_for_page(self, page_id: int) -> list[str]:
        regions = self.list_for_page(page_id)
        paths: list[str] = []
        region_ids = [region.id for region in regions]
        for region in regions:
            paths.extend([region.crop_path, region.mask_path])
        if region_ids:
            self.session.execute(delete(Embedding).where(Embedding.region_id.in_(region_ids)))
            self.session.execute(delete(RegionLabel).where(RegionLabel.region_id.in_(region_ids)))
            self.session.execute(delete(Region).where(Region.id.in_(region_ids)))
            self.session.flush()
        return paths

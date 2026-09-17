from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class IngestStatus(BaseModel):
    state: str
    message: str = ""
    current_file: str = ""
    files_total: int = 0
    files_done: int = 0
    pages_done: int = 0
    pages_total: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class SearchRequestMeta(BaseModel):
    kind: str | None = Field(default=None, description="loose_part | subassembly")
    top_k: int | None = None


class SearchHit(BaseModel):
    score: float
    kind: str
    region_id: int
    page_id: int
    page_number: int
    book_id: int
    book_number: int
    set_id: int
    set_name: str
    step_number: int | None = None
    bag_number: int | None = None
    raster_path: str
    thumb_path: str
    crop_path: str


class SearchResponse(BaseModel):
    query_id: int
    kind: str
    results: list[SearchHit]


class SetOut(BaseModel):
    id: int
    set_num: str | None
    name: str
    book_count: int = 0
    page_count: int = 0


class BookOut(BaseModel):
    id: int
    set_id: int
    set_name: str
    book_number: int
    source_relpath: str
    page_count: int
    source_missing: bool
    ingest_status: str


class PageOut(BaseModel):
    id: int
    book_id: int
    page_number: int
    raster_path: str
    thumb_path: str
    width: int
    height: int
    step_number: int | None = None
    bag_number: int | None = None


class RegionCropOut(BaseModel):
    id: int
    kind: str
    crop_path: str
    mask_path: str
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int


class PageDetail(PageOut):
    set_name: str
    book_number: int
    crops: list[RegionCropOut] = Field(default_factory=list)
    prev_page_id: int | None = None
    next_page_id: int | None = None


class FeedbackRequest(BaseModel):
    query_id: int
    correct_page_id: int | None = None
    correct_region_id: int | None = None

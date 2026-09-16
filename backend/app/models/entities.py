from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Set(Base):
    __tablename__ = "sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_num: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    books: Mapped[list["Book"]] = relationship(back_populates="set")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("sets.id"), nullable=False)
    book_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_relpath: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_missing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ingest_status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")

    set: Mapped[Set] = relationship(back_populates="books")
    pages: Mapped[list["Page"]] = relationship(back_populates="book")


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("book_id", "page_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raster_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    thumb_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)

    book: Mapped[Book] = relationship(back_populates="pages")
    steps: Mapped[list["Step"]] = relationship(back_populates="page")
    regions: Mapped[list["Region"]] = relationship(back_populates="page")


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id"), nullable=False)
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bag_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    page: Mapped[Page] = relationship(back_populates="steps")


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    bbox_x: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_w: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_h: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mask_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    page: Mapped[Page] = relationship(back_populates="regions")
    labels: Mapped[list["RegionLabel"]] = relationship(back_populates="region")
    embeddings: Mapped[list["Embedding"]] = relationship(back_populates="region")


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    design_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")


class Color(Base):
    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lego_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    hex: Mapped[str] = mapped_column(String(7), nullable=False, default="#888888")


class RegionLabel(Base):
    __tablename__ = "region_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), nullable=False)
    part_id: Mapped[int | None] = mapped_column(ForeignKey("parts.id"), nullable=True)
    color_id: Mapped[int | None] = mapped_column(ForeignKey("colors.id"), nullable=True)
    qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="vision")

    region: Mapped[Region] = relationship(back_populates="labels")
    part: Mapped[Part | None] = relationship()
    color: Mapped[Color | None] = relationship()


class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (UniqueConstraint("region_id", "model_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    silhouette: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    region: Mapped[Region] = relationship(back_populates="embeddings")


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mask_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    predicted_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    override_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    topk_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    correct_page_id: Mapped[int | None] = mapped_column(ForeignKey("pages.id", ondelete="SET NULL"), nullable=True)
    correct_region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id", ondelete="SET NULL"), nullable=True)

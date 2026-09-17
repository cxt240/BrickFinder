from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    backend_port: int = 8080
    vision_port: int = 8081
    vision_url: str = ""
    brickfinder_role: str = "backend"
    instructions_path: Path = Path("/instructions")
    data_path: Path = Path("/data")
    ingest_dpi: int = 150
    embedding_model: str = "dinov2-small"
    search_rerank_model: str = "clip-vit-b-32"
    search_rerank_candidates: int = 100
    top_k: int = 12
    search_hist_weight: float = 0.55
    search_silhouette_weight: float = 0.45
    search_chroma_weight: float = 0.0
    search_kind_boost: float = 0.03
    jpeg_quality: int = 85
    thumb_width: int = 240

    @property
    def db_dir(self) -> Path:
        return self.data_path / "db"

    @property
    def db_path(self) -> Path:
        return self.db_dir / "brickfinder.db"

    @property
    def media_path(self) -> Path:
        return self.data_path / "media"

    @property
    def ingest_status_path(self) -> Path:
        return self.data_path / "ingest_status.json"

    @property
    def sqlite_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"


@lru_cache
def get_config() -> Config:
    return Config()

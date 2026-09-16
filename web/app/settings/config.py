from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    backend_url: str = "http://backend:8080"
    web_port: int = 3000
    ui_dist: Path = Path("/app/ui/dist")


@lru_cache
def get_config() -> Config:
    return Config()

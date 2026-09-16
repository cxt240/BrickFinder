from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Secrets(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    rebrickable_api_key: str | None = Field(default=None)


@lru_cache
def get_secrets() -> Secrets:
    secrets = Secrets()
    if secrets.rebrickable_api_key == "":
        secrets.rebrickable_api_key = None
    return secrets

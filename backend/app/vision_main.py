from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.endpoints import health, vision
from app.services.embedding_service import create_embedding_service
from app.settings.config import get_config


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config = get_config()
    create_embedding_service(config.embedding_model)
    if config.search_rerank_model:
        create_embedding_service(config.search_rerank_model)
    yield


app = FastAPI(title="BrickFinder Vision", lifespan=lifespan)
app.include_router(health.router)
app.include_router(vision.router)

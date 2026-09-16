from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.endpoints import catalog, feedback, health, ingest, media, search
from app.settings.config import get_config


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config = get_config()
    init_db(config)
    yield


app = FastAPI(title="BrickFinder", lifespan=lifespan)
app.include_router(health.router)
app.include_router(search.router)
app.include_router(catalog.router)
app.include_router(ingest.router)
app.include_router(media.router)
app.include_router(feedback.router)

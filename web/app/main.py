from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.endpoints import catalog, feedback, health, ingest, media, search
from app.services.backend_client import BackendClient
from app.settings.config import get_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = BackendClient()
    app.state.backend = client
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(title="BrickFinder Web", lifespan=lifespan)
app.include_router(health.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")


@app.exception_handler(httpx.HTTPStatusError)
async def backend_status(_request: Request, exc: httpx.HTTPStatusError) -> JSONResponse:
    detail = exc.response.text
    try:
        payload = exc.response.json()
        detail = payload.get("detail", detail)
    except Exception:
        pass
    return JSONResponse({"detail": detail}, status_code=exc.response.status_code)


@app.exception_handler(httpx.RequestError)
async def backend_unreachable(_request: Request, exc: httpx.RequestError) -> JSONResponse:
    return JSONResponse({"detail": f"Backend unreachable: {exc}"}, status_code=502)

ui_dist = get_config().ui_dist
assets = ui_dist / "assets"
if assets.is_dir():
    app.mount("/assets", StaticFiles(directory=assets), name="assets")


@app.get("/{full_path:path}")
async def spa(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        return JSONResponse({"detail": "Not found"}, status_code=404)
    if not ui_dist.exists():
        return JSONResponse({"detail": "UI bundle missing"}, status_code=500)
    candidate = ui_dist / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)
    index = ui_dist / "index.html"
    return FileResponse(index)

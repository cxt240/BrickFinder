# Architecture

## Topology

```
Browser  →  web (BFF + React static)  →  backend (FastAPI)
            :3000                         sqlite + /data/media
                                          Instructions bind-mount (ingest only)
                                          ↓ VISION_URL  POST /embed
                                     vision (DINOv2 + CLIP)
                                          :8081, not published
```

Compose: `vision`, `backend`, `web`, and profiles `ingest` / `reindex`. The browser never reaches the backend or vision. `web` proxies `/api/media` so image URLs stay same-origin.

HTTP groups (backend, mirrored by the BFF under `/api`):

| Group | Paths |
| --- | --- |
| health | `GET /health` |
| search | `POST /search` |
| catalog | `GET /sets`, `GET /books`, `GET /books/{id}/pages`, `GET /pages/{id}` |
| ingest | `GET /ingest/status`, `POST /ingest/run` |
| media | `GET /media/{relpath}` |
| feedback | `POST /feedback` |

Vision (not on the BFF): `GET /health`, `POST /embed`.

## Why this exists

Official catalogs identify a brick in the abstract. BrickFinder answers: **which page of these local instruction books matches this photo** (loose part or subassembly).

OCR/PDF text is for page, step, bag, and quantity. Callouts are drawings; they are cropped and embedded, not OCRed into part names.

## Why vision is a sidecar

Torch + DINOv2-small + CLIP take tens of seconds (or minutes on first download) to load. Keeping them in the domain API meant every ranking tweak waited on model load.

**vision** is the same `backend/` Python package in a second image (`Dockerfile.vision`): torch and `transformers` live only there. **backend** is slim (FastAPI, sqlite, PDF, numpy). `RemoteEmbeddingService` implements the same `EmbeddingService` surface over HTTP.

That is a sidecar API, not a public one: port 8081 is unpublished, the browser never calls it, ingest/search/reindex share one warm process. A third-party “vision microservice” with its own schema would be the same HTTP boundary with more ceremony.

`BRICKFINDER_ROLE=vision` stops the vision process from calling `VISION_URL` (no recursion). Histogram embeddings stay in-process on the backend; they do not need torch.

## Ingest

1. Discover `*.pdf` under `/instructions`.
2. SHA-256 skip / resume incomplete / mark missing sources (no prune).
3. Raster pages with PyMuPDF at `INGEST_DPI` (default 150).
4. Pull step/bag from the PDF text layer (`OcrService`; real OCR can replace this later).
5. Heuristic layout: assembly crop (right side) + callout strip (left).
6. Mask near-white backgrounds; store mask PNGs.
7. Embed each crop via `EmbeddingService` (`dinov2-small` by default; `histogram-hsv-256` is still available). Backend/ingest POST crops to vision. Vectors are float32 blobs on `embeddings` keyed by `model_name`.

Status is written to `/data/ingest_status.json` so the UI can poll.

Re-embed without re-raster: `python -m app.reindex` (Compose profile `reindex`). Use `docker compose --profile reindex run --rm --no-deps reindex` so the API is not SIGTERM’d. Vision must already be running.

## Search

1. Save the upload under `/data/media/queries`.
2. Foreground mask (`MaskService`).
3. Gate: compact isolated object → `loose_part`, else `subassembly`. Client may override.
4. Embed with the same model used at ingest (`dinov2-small` by default) through vision.
5. kNN over assembly and callout regions. For DINO, candidate score is raw cosine (plus a small preferred-kind boost) so CLIP sees true neighbors.
6. CLIP re-ranks the top `SEARCH_RERANK_CANDIDATES` (default 100) page hits at search time by embedding the query photo and each candidate crop. CLIP vectors are not stored.
7. Return top-k pages with scores. Persist the attempt on `queries` for later feedback.

## Domain gap

User photos are not instruction CGI. DINOv2-small is the default embedder (`Dinov2EmbeddingService`, `facebook/dinov2-small`, 384-d). CLIP (`ClipEmbeddingService`, `openai/clip-vit-base-patch32`) is search-time only. Histogram + silhouette remains as `histogram-hsv-256`.

Common plates appear on many pages; the UI shows a ranked list, not a single fake answer.

## Layer map

See [AGENTS.md](../AGENTS.md). Backend and BFF routers: health, search, catalog, ingest, media, feedback. Vision router `embed` is backend-package only. BFF exposes UI view-models of the same verbs. Hugging Face weights cache at `{DATA_PATH}/models/hf`.

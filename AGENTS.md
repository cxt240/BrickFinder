# Agent notes

BrickFinder is a Dockerized local LEGO instruction search app. Read this before changing code.

## Services

- **vision** — DINOv2 + CLIP FastAPI on port 8081 (internal). Same `backend/` package, `Dockerfile.vision`, entry `app.vision_main`. Owns torch/transformers and the Hugging Face cache under `/data/models/hf`. No sqlite.
- **backend** — domain FastAPI on port 8080 (internal). Owns sqlite, ingest orchestration, search ranking. Slim image (no torch). Calls vision at `VISION_URL` via `RemoteEmbeddingService`.
- **web** — React SPA + Python BFF in **one** container. Browser origin is the BFF. `/api/*` is BFF; everything else is the UI.
- **ingest** — same image as backend, Compose profile `ingest`, one-shot `python -m app.ingest`. Needs vision healthy.
- **reindex** — same image as backend, Compose profile `reindex`, one-shot `python -m app.reindex`. Never `docker compose run backend` for this (it SIGTERMs the API). Prefer `--no-deps` while the stack is up so backend is not recreated; vision must already be running.

There is no separate `frontend` or `bff` service. Do not teach the browser to call the backend or vision.

API groups (backend path → same path under `/api` on the BFF): **health** `/health`, **search** `/search`, **catalog** `/sets` `/books` `/pages`, **ingest** `/ingest`, **media** `/media`, **feedback** `/feedback`. One router module per group. Health is not mixed into search or catalog.

Vision-only (not mirrored by the BFF): **vision** `/embed`.

## Layers

| Folder | Allowed | Forbidden |
| --- | --- | --- |
| `endpoints/` | HTTP, validation, call one manager | SQL, model inference, third-party HTTP |
| `managers/` | One use case, repos + services, transactions | FastAPI request objects, raw SQL strings in loops |
| `services/` | PDF, OCR/text, layout, mask, embed, HTTP clients | SQLAlchemy sessions |
| `repositories/` | Queries and writes | FastAPI, vision, HTTP |

`web/app/services/` is only `BackendClient`. The BFF has no sqlite. The BFF does not call vision.

## Code layout

One public class per file in `managers/`, `repositories/`, and `services/` (backend and BFF). Name the module after the class: `SearchManager` → `search_manager.py`. Do not add a second manager, repo, or service to an existing file for convenience.

Package `__init__.py` files may re-export those classes. They must not contain implementations.

Endpoints: one FastAPI router module per API group (`health.py`, `search.py`, `catalog.py`, `ingest.py`, `media.py`, `feedback.py`). Do not mix health into search or catalog. The BFF mirrors the same split under `web/app/endpoints/` and the same paths under `/api`. Vision adds `vision.py` (`POST /embed`) on the vision process only — not a BFF group.

Small helper dataclasses (`RegionBox`, `EmbeddedView`, …) stay in the service file that owns them. A new embedding model (CLIP/DINOv2) is a **new class in a new file** behind the `EmbeddingService` interface, not a branch stuffed into `embedding_service.py`. Remote HTTP to the sidecar is `RemoteEmbeddingService`.

## Settings

- `settings/config.py` — ports, paths, DPI, model name, weights, `vision_url`, `brickfinder_role`. Defaults are fine for Compose.
- `settings/secrets.py` — credentials from env only (`REBRICKABLE_API_KEY` optional). Never log secret values.
- Commit `.env.example`. Gitignore `.env`.

The vision container must set `BRICKFINDER_ROLE=vision` and must not set `VISION_URL`. Backend/ingest/reindex set `VISION_URL=http://vision:8081`.

## Ingest is additive

Walk `INSTRUCTIONS_PATH` for `*.pdf`. Identity is **content SHA-256**:

- Known complete hash → skip (update path if the file moved).
- Unknown hash → ingest.
- Incomplete hash → wipe that book’s derived rows/files and re-ingest (crash recovery only).
- PDF missing on disk → set `books.source_missing = true`. **Never** delete pages, regions, embeddings, or media because a source file disappeared.
- Same path, new hash → new book row; keep the old one.

Parent folder name is the set display name.

## Search

`SearchManager`: mask → part vs subassembly gate → `EmbeddingService` (default `dinov2-small`, usually `RemoteEmbeddingService`) → kNN → optional CLIP re-rank of the top candidates (`clip-vit-b-32`).

v1 model name is `histogram-hsv-256` (in-process on the backend). Default index model is `dinov2-small` (`Dinov2EmbeddingService` in the vision container). CLIP is a separate class used as a search-time re-ranker, not a second full index. A new backbone is a new class in a new file behind `EmbeddingService`, stored under a new `model_name`. Re-embed with `python -m app.reindex` (Compose profile `reindex`) — do not `docker compose run backend`, which stops the API.

## Schema

Canonical tables: [docs/SCHEMA.md](docs/SCHEMA.md). Keep that file in sync with `backend/app/models/entities.py`.

## Media

All derived files live under `{DATA_PATH}/media`. SQLite is `{DATA_PATH}/db/brickfinder.db` (Compose bind-mount `./data` → `/data`). Database stores media paths relative to `DATA_PATH`. Serve only files inside that tree. Hugging Face weights live under `{DATA_PATH}/models/hf` (vision container).

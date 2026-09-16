# Agent notes

BrickFinder is a Dockerized local LEGO instruction search app. Read this before changing code.

## Services

- **backend** — domain FastAPI on port 8080 (internal). Owns sqlite, vision, ingest.
- **web** — React SPA + Python BFF in **one** container. Browser origin is the BFF. `/api/*` is BFF; everything else is the UI.
- **ingest** — same image as backend, Compose profile `ingest`, one-shot `python -m app.ingest`.

There is no separate `frontend` or `bff` service. Do not teach the browser to call the backend.

API groups (backend path → same path under `/api` on the BFF): **health** `/health`, **search** `/search`, **catalog** `/sets` `/books` `/pages`, **ingest** `/ingest`, **media** `/media`, **feedback** `/feedback`. One router module per group. Health is not mixed into search or catalog.

## Layers

| Folder | Allowed | Forbidden |
| --- | --- | --- |
| `endpoints/` | HTTP, validation, call one manager | SQL, model inference, third-party HTTP |
| `managers/` | One use case, repos + services, transactions | FastAPI request objects, raw SQL strings in loops |
| `services/` | PDF, OCR/text, layout, mask, embed, HTTP clients | SQLAlchemy sessions |
| `repositories/` | Queries and writes | FastAPI, vision, HTTP |

`web/app/services/` is only `BackendClient`. The BFF has no sqlite.

## Code layout

One public class per file in `managers/`, `repositories/`, and `services/` (backend and BFF). Name the module after the class: `SearchManager` → `search_manager.py`. Do not add a second manager, repo, or service to an existing file for convenience.

Package `__init__.py` files may re-export those classes. They must not contain implementations.

Endpoints: one FastAPI router module per API group (`health.py`, `search.py`, `catalog.py`, `ingest.py`, `media.py`, `feedback.py`). Do not mix health into search or catalog. The BFF mirrors the same split under `web/app/endpoints/` and the same paths under `/api`.

Small helper dataclasses (`RegionBox`, `EmbeddedView`, …) stay in the service file that owns them. A new embedding model (CLIP/DINOv2) is a **new class in a new file** behind the `EmbeddingService` interface, not a branch stuffed into `embedding_service.py`.

## Settings

- `settings/config.py` — ports, paths, DPI, model name, weights. Defaults are fine for Compose.
- `settings/secrets.py` — credentials from env only (`REBRICKABLE_API_KEY` optional). Never log secret values.
- Commit `.env.example`. Gitignore `.env`.

## Ingest is additive

Walk `INSTRUCTIONS_PATH` for `*.pdf`. Identity is **content SHA-256**:

- Known complete hash → skip (update path if the file moved).
- Unknown hash → ingest.
- Incomplete hash → wipe that book’s derived rows/files and re-ingest (crash recovery only).
- PDF missing on disk → set `books.source_missing = true`. **Never** delete pages, regions, embeddings, or media because a source file disappeared.
- Same path, new hash → new book row; keep the old one.

Parent folder name is the set display name.

## Search

`SearchManager`: mask → part vs subassembly gate (overridable) → `EmbeddingService` → kNN on float32 blobs → silhouette re-rank.

v1 model name is `histogram-hsv-256`. CLIP/DINOv2 should be a new class behind the same `EmbeddingService` interface, stored under a new `model_name`.

## Schema

Canonical tables: [docs/SCHEMA.md](docs/SCHEMA.md). Keep that file in sync with `backend/app/models/entities.py`.

## Media

All derived files live under `{DATA_PATH}/media`. SQLite is `{DATA_PATH}/db/brickfinder.db` (Compose bind-mount `./data` → `/data`). Database stores media paths relative to `DATA_PATH`. Serve only files inside that tree.

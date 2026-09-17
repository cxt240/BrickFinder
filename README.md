# BrickFinder

Local LEGO instruction search. Photograph a loose part or a still-together chunk, and BrickFinder ranks the best-matching pages from the PDFs you keep on disk.

Search never leaves your machine. A Rebrickable API key is optional (catalog snapshot only) and is not required to ingest or match pages.

The UCS Venator (75367) PDFs in `Instructions/UCS Venator/` are the first set. Everything runs in Docker — no host Python or Node install.

## Run

1. Install Docker Desktop.
2. Put instruction PDFs under `Instructions/<Set Name>/`. The parent folder name is the set display name in the UI.
3. Copy `.env.example` to `.env` (`copy .env.example .env` on Windows). Tune ports and ingest DPI there if you want; leave `REBRICKABLE_API_KEY` empty unless you use that optional catalog snapshot. `.env` is gitignored.
4. Start the app:

```bash
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). The browser talks only to the web container. Domain FastAPI stays on port 8080 inside Compose. DINOv2 and CLIP live in a separate **vision** container (port 8081, internal only). First vision start downloads Hugging Face weights into `data/models/hf/` (gitignored) and can take a few minutes; later starts reuse that cache.

First ingest of large booklets is slow (hundreds of pages at 150 DPI, plus a DINO pass per crop). Use **Index instructions** in the UI, or the one-shot ingest profile:

```bash
docker compose --profile ingest run --rm ingest
```

Ingest is additive: new PDFs are hashed (content SHA-256) and indexed; already-indexed hashes are skipped; deleting a PDF marks the book source missing and does **not** remove pages or embeddings.

## Use

The bar at the top of every page shows ingest state (idle / running / done, current file, file and page progress). **Index instructions** starts a background ingest against `Instructions/`.

**Search** (`/`):

- Upload a photo or use the camera. JPEG, PNG, WebP, and HEIC/HEIF are fine.
- Leave kind on **Auto detect**, or force **Subassembly** vs **Loose part**.
- **Search** returns a ranked list of page guesses. Click a thumbnail to open that page.
- If a guess is right, **This is the page** records it so later ranking can use the feedback.

**Books** (`/books`):

- Pick a set, then a booklet, then a page thumbnail.
- On a page (`/pages/:id`), use **Previous page** / **Next page** or the arrow keys. Indexed crops (assembly vs callout) sit under the raster; click a crop card to overlay that region on the page.

Until ingest finishes at least once, Search and Books will be empty.

## How matching works

Phone photos are not instruction CGI. A color histogram cannot reliably match a printed sticker or a built chunk to the booklet drawing, so the default index is a vision transformer:

1. **Ingest** embeds each assembly and callout crop with **DINOv2-small** (`facebook/dinov2-small`, 384-d CLS). Vectors are stored on `embeddings` under `model_name=dinov2-small`.
2. **Search** embeds the query the same way, then does cosine kNN over both region kinds.
3. **CLIP** (`openai/clip-vit-base-patch32`) re-ranks the top ~100 DINO page candidates at query time. CLIP is not a second full index.

Histogram + silhouette (`histogram-hsv-256`) is still available if you set `EMBEDDING_MODEL` and reindex. Changing the index model does not re-raster PDFs; it only rewrites embedding rows:

```bash
docker compose --profile reindex run --rm --no-deps reindex
```

`--no-deps` keeps Compose from recreating **backend**. Vision must already be up (it is, if you started the stack with `compose up`). Do not `docker compose run backend` — that SIGTERMs the API.

## Project structure

```
Browser  →  web (React UI + Python BFF)  →  backend (FastAPI, sqlite, ingest)
            :3000  /api/* and the SPA         :8080 internal only
                                              ↓ HTTP /embed
                                         vision (DINOv2 + CLIP)
                                              :8081 internal only
```

There is no separate frontend or BFF service. The browser must not call the backend or vision.

| Path | Role |
| --- | --- |
| `backend/` | Domain API: ingest, search, catalog, sqlite. Slim image (no torch). |
| `backend/Dockerfile.vision` | Sidecar image: torch + transformers, `app.vision_main` |
| `web/` | React SPA (`web/ui`) + Python BFF (`web/app`) in **one** container |
| `Instructions/` | Source PDFs (gitignored). Bind-mounted read-only into backend/ingest |
| `data/` | Local volume (gitignored). SQLite at `data/db/brickfinder.db`; rasters at `data/media/`; HF weights at `data/models/hf/` |
| `docs/` | [ARCHITECTURE.md](docs/ARCHITECTURE.md) (flows) and [SCHEMA.md](docs/SCHEMA.md) (tables) |

Compose services: **vision** (DINO/CLIP, always on), **backend** (always on, waits for vision), **web** (published on 3000), **ingest** (profile `ingest`, new PDFs), **reindex** (profile `reindex`, rewrite embeddings for the current `EMBEDDING_MODEL`).

Vision is a sidecar HTTP API, not a public API. Backend code changes (search ranking, catalog, ingest orchestration) rebuild the slim image and come up in seconds. Model-weight changes still rebuild/restart **vision** only.

### Backend layers

One class per file, roughly:

| Folder | Does |
| --- | --- |
| `endpoints/` | HTTP + validation, then one manager |
| `managers/` | One use case: repos + services, transactions |
| `services/` | PDF, OCR/text, layout, mask, embed, images, HTTP clients |
| `repositories/` | Queries and writes |
| `settings/config.py` | Ports, paths, DPI, model name, search weights, `VISION_URL` |
| `settings/secrets.py` | Credentials from env only (`REBRICKABLE_API_KEY`) |

`create_embedding_service` returns `RemoteEmbeddingService` when `VISION_URL` is set (backend, ingest, reindex). The vision container sets `BRICKFINDER_ROLE=vision` and loads `Dinov2EmbeddingService` / `ClipEmbeddingService` locally.

### Web

`web/ui` is the React app (Search, Books, page viewer). `web/app` is the BFF: it proxies `/api/*` to the backend via `BackendClient` and has no sqlite. Same route groups as the backend, mounted under `/api`.

### `/api` paths (BFF)

Same paths on the backend without the `/api` prefix.

| Group | Paths |
| --- | --- |
| health | `GET /api/health` |
| search | `POST /api/search` |
| catalog | `GET /api/sets`, `GET /api/books`, `GET /api/books/{id}/pages`, `GET /api/pages/{id}` |
| ingest | `GET /api/ingest/status`, `POST /api/ingest/run` |
| media | `GET /api/media/{relpath}` |
| feedback | `POST /api/feedback` |

Vision `POST /embed` is not on the BFF.

Changing code? Start with [AGENTS.md](AGENTS.md).

## License

You may clone, run, and modify BrickFinder for noncommercial use. For-profit use is reserved to the creator. See [LICENSE](LICENSE) (PolyForm Noncommercial License 1.0.0).

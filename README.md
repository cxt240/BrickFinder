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

Open [http://localhost:3000](http://localhost:3000). The browser talks only to the web container. Backend FastAPI stays on port 8080 inside Compose.

First ingest of large booklets is slow (hundreds of pages at 150 DPI). Use **Index instructions** in the UI, or the one-shot ingest profile:

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
- On a page (`/pages/:id`), use **Previous page** / **Next page**. Indexed crops (assembly vs callout) show under the full raster.

Until ingest finishes at least once, Search and Books will be empty.

## Project structure

```
Browser  →  web (React UI + Python BFF)  →  backend (FastAPI, sqlite, vision)
            :3000  /api/* and the SPA         :8080 internal only
```

There is no separate frontend or BFF service. The browser must not call the backend.

| Path | Role |
| --- | --- |
| `backend/` | Domain API: ingest, search, catalog, sqlite, embeddings |
| `web/` | React SPA (`web/ui`) + Python BFF (`web/app`) in **one** container |
| `Instructions/` | Source PDFs (gitignored). Bind-mounted read-only into backend/ingest |
| `data/` | Local volume (gitignored). SQLite at `data/db/brickfinder.db`; rasters and query images at `data/media/` |
| `docs/` | [ARCHITECTURE.md](docs/ARCHITECTURE.md) (flows) and [SCHEMA.md](docs/SCHEMA.md) (tables) |

Compose services: **backend** (always on), **web** (published on 3000), **ingest** (same image as backend, profile `ingest`, `python -m app.ingest`). `./data` → `/data`; `./Instructions` → `/instructions`.

### Backend layers

One class per file, roughly:

| Folder | Does |
| --- | --- |
| `endpoints/` | HTTP + validation, then one manager |
| `managers/` | One use case: repos + services, transactions |
| `services/` | PDF, OCR/text, layout, mask, embed, images |
| `repositories/` | Queries and writes |
| `settings/config.py` | Ports, paths, DPI, model name, search weights |
| `settings/secrets.py` | Credentials from env only (`REBRICKABLE_API_KEY`) |

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

Changing code? Start with [AGENTS.md](AGENTS.md).

## License

You may clone, run, and modify BrickFinder for noncommercial use. For-profit use is reserved to the creator. See [LICENSE](LICENSE) (PolyForm Noncommercial License 1.0.0).

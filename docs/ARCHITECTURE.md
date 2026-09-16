# Architecture

## Topology

```
Browser  →  web (BFF + React static)  →  backend (FastAPI)
                                         sqlite + /data/media
                                         Instructions bind-mount (ingest only)
```

Compose: `backend`, `web`, and profile `ingest`. The browser never reaches the backend. `web` proxies `/api/media` so image URLs stay same-origin.

HTTP groups (backend, mirrored by the BFF under `/api`):

| Group | Paths |
| --- | --- |
| health | `GET /health` |
| search | `POST /search` |
| catalog | `GET /sets`, `GET /books`, `GET /books/{id}/pages`, `GET /pages/{id}` |
| ingest | `GET /ingest/status`, `POST /ingest/run` |
| media | `GET /media/{relpath}` |
| feedback | `POST /feedback` |

## Why this exists

Official catalogs identify a brick in the abstract. BrickFinder answers: **which page of these local instruction books matches this photo** (loose part or subassembly).

OCR/PDF text is for page, step, bag, and quantity. Callouts are drawings; they are cropped and embedded, not OCRed into part names.

## Ingest

1. Discover `*.pdf` under `/instructions`.
2. SHA-256 skip / resume incomplete / mark missing sources (no prune).
3. Raster pages with PyMuPDF at `INGEST_DPI` (default 150).
4. Pull step/bag from the PDF text layer (`OcrService`; real OCR can replace this later).
5. Heuristic layout: assembly crop (right side) + callout strip (left).
6. Mask near-white backgrounds; store mask PNGs.
7. Histogram embedding via `EmbeddingService`; float32 blobs on `embeddings`.

Status is written to `/data/ingest_status.json` so the UI can poll.

## Search

1. Save the upload under `/data/media/queries`.
2. Foreground mask (`MaskService`).
3. Gate: compact isolated object → `loose_part`, else `subassembly`. Client may override.
4. Embed with the same model used at ingest.
5. kNN over regions of that kind; re-rank with silhouette cosine.
6. Return top-k pages with scores. Persist the attempt on `queries` for later feedback.

## Domain gap

User photos are not instruction CGI. Histogram + silhouette is the v1 baseline (distinctive Venator chunks should land near the right booklet/page). CLIP/DINOv2 plugs into `EmbeddingService` without changing managers.

Common plates appear on many pages; the UI shows a ranked list, not a single fake answer.

## Layer map

See [AGENTS.md](../AGENTS.md). Backend and BFF routers: health, search, catalog, ingest, media, feedback. BFF exposes UI view-models of the same verbs.

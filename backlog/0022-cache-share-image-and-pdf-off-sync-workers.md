---
id: 0022
title: Cache/offload og:image and PDF rendering so they stop blocking sync Gunicorn workers
type: change
status: shipped
created: 2026-08-04
branch: feature/cache-share-image-and-pdf
---

## Request
`share_image` and `download_pdf` both do CPU-heavy synchronous rendering inline on the request thread, and prod only runs 3 sync Gunicorn workers — a handful of concurrent social-crawler fetches or PDF downloads can exhaust the whole worker pool and stall the survey for everyone.

## Investigation
From the codebase-audit performance lens (2026-08-04):
- `app/survey/routes.py:306` — `share_image` calls `cairosvg.svg2png(...)` inline per request. Output is deterministic per submission (route already sends `Cache-Control: immutable`) but nothing caches it server-side, so every hit re-rasterises from scratch. This URL is exposed as `og:image`, which social crawlers auto-fetch, often several near-concurrent times per share.
- `app/survey/routes.py:317` — `download_pdf` runs WeasyPrint (`HTML(...).write_pdf()`) inline; typically hundreds of ms to seconds, and also re-fetches the Bootstrap CDN stylesheet via `base_url`. The email path already generates the same PDF off-thread; the download path doesn't.
- `deploy/monkeypuzzle.service:11` — Gunicorn runs `--workers 3`, default sync worker class (one request per worker, no threads), which is what turns these into an actual stall risk rather than just wasted CPU.

## Notes
Suggested fix direction (from the auditor, not yet scoped): cache the rendered PNG (on-disk keyed by token, or small LRU) and reuse/cache the generated PDF per submission the same way the email path already does; alternatively move rasterisation/PDF generation off the sync workers (async worker class or threads).

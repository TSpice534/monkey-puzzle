# The Monkey Puzzle

A quick, graphical, no-login self-assessment that outputs a personalised sustainability
**persona** — "your sustainable who." The first question asks whether you're answering
as an individual or on behalf of an organisation, then tailors the rest of the questions
to that — answer the ones that apply to you, get one of nine profiles, and share the
result.

Framing is **"know yourself"** — not measuring what you're doing wrong, but finding your
sweet spot. No account needed. Open source.

## The nine personas

Accountant · Implementer · Developer · Advocate · Communicator · Activist · Connector ·
Cooperator · Entrepreneur

Each result comes with a persona card: description, natural allies ("brethren"), good
collaborators ("besties"), likely friction points ("battlers"), and 2–3 curated case
studies and resources.

## Status

Phases 1–5 of the build plan are done: a data-driven survey flow, persona classifier,
result page (with a radar "fingerprint" chart), and sharing/output all work end-to-end
against a placeholder question set — OpenGraph/Twitter share tags, a generated PNG share
image, a LinkedIn share link, a downloadable PDF report, and an opt-in "email me a copy".
Only deploy (Phase 6) is left. Forked from the Donut Toolkit as a starting framework,
then diverging: no accounts, public/viral, single categorical persona output. See
[docs/PRODUCTION-PLAN.md](docs/PRODUCTION-PLAN.md) for the full plan and phasing.

Primary pilot: the Federation of Music Conferences (32 conferences), extending later to
European cultural and business events.

## How it's built

- **Stack:** Python 3.12 / Flask / SQLAlchemy / SQLite (dev) → Postgres (prod) /
  WeasyPrint (PDF) / Flask-Mail (optional email) / Flask-Limiter (rate limiting) /
  cairosvg (PNG share image) / Bootstrap via CDN (no build step, no Alpine.js — the
  survey widgets are native HTML/CSS with one small vanilla script).
- **Data-driven content:** all questions, weights, and personas live in
  `content/survey.yaml` — editable without touching code. Question set and scoring are
  designed by Rob and Andrew; the engine is built to consume whatever they deliver. The
  content shipped today is realistic placeholder content.
- **Individual/organisation routing:** the survey's first question sets which of the
  rest of the questions show — any question can be tagged for one track or left shared.
  That's a YAML-only decision (`audience: [individual]` / `[organisation]`); no code
  changes needed to add or retag a branch question.
- **No accounts:** submissions are anonymous, keyed by a random token that powers the
  shareable result link and optional emailed copy. The email address used for "email me
  a copy" is never persisted — it's used once to send that message and then discarded.

## Running the quiz locally

```bash
source .venv/bin/activate
flask db upgrade   # first time only, or after pulling new migrations
flask run
```

Visit `/`, click "Begin", and work through the survey — each step is one question, and
finishing the last one classifies your answers into one of the nine personas and shows
the result page with your fingerprint radar chart, a downloadable PDF, and a share image.

PDF generation needs libpango installed (`brew install pango` on macOS — `.flaskenv`
already sets `DYLD_LIBRARY_PATH` for it). "Email me a copy" is a no-op with a flash
message until `MAIL_SERVER` (and friends — see `config.py`) are set in the environment.

## Repo conventions

- Work on `dev`; `main` is production. Never push straight to `main`.
- Backlog items live in `backlog/` (filed via the AIOS `/request` flow).

## Licence

MIT — see [LICENSE](LICENSE).

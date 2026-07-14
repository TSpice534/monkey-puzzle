# The Monkey Puzzle

A quick, graphical, no-login self-assessment that outputs a personalised sustainability
**persona** — "your sustainable who." Answer 10–15 questions, get one of nine profiles,
and share the result.

Framing is **"know yourself"** — not measuring what you're doing wrong, but finding your
sweet spot. No account needed. Open source.

## The nine personas

Documenter · Implementer · Developer · Advocate · Communicator · Activist · Connector ·
Cooperator · Entrepreneur

Each result comes with a persona card: description, natural allies ("brethren"), good
collaborators ("besties"), likely friction points ("battlers"), and 2–3 curated case
studies and resources.

## Status

Early build. Forked from the Donut Toolkit as a starting framework, then diverging:
no accounts, public/viral, single categorical persona output. See
[docs/PRODUCTION-PLAN.md](docs/PRODUCTION-PLAN.md) for the full plan and phasing.

Primary pilot: the Federation of Music Conferences (32 conferences), extending later to
European cultural and business events.

## How it's built

- **Stack:** Python 3.12 / Flask / SQLAlchemy / SQLite (dev) → Postgres (prod) /
  WeasyPrint (PDF) / Bootstrap + Alpine.js via CDN (no build step).
- **Data-driven content:** all questions, weights, and personas live in
  `content/survey.yaml` — editable without touching code. Question set and scoring are
  designed by Rob and Andrew; the engine is built to consume whatever they deliver.
- **No accounts:** submissions are anonymous, keyed by a random token that powers the
  shareable result link and optional emailed copy.

## Repo conventions

- Work on `dev`; `main` is production. Never push straight to `main`.
- Backlog items live in `backlog/` (filed via the AIOS `/request` flow).

## Licence

MIT — see [LICENSE](LICENSE).

# The Monkey Puzzle — Initial Production Plan

## Context

Tom is building a new platform, **The Monkey Puzzle** — a quick, graphical, no-login
self-assessment that outputs a personalised sustainability *persona* ("your sustainable
who"): one of nine profiles (Accountant, Implementer, Developer, Advocate, Communicator,
Activist, Connector, Cooperator, Entrepreneur). Framing is "know yourself," not
"measure what you're doing wrong." Primary pilot: the Federation of Music Conferences
(32 conferences), later extending to European cultural/business events.

Andrew and Rob own the **question set and scoring design**; Tom owns the **build**. The
real questions are not ready and won't be for a while, so this plan builds a
**data-driven engine plus a realistic placeholder question set** (derived from Rob's
framework in the brainstorm notes) so the platform is demonstrable end-to-end today and
becomes a simple data swap when the real content lands.

**Decisions locked (2026-07-14):**
1. **New standalone repo**, seeded from the Donut Toolkit — not a new Donut client.
2. **Data-driven question set** (YAML/JSON), editable by Rob/Andrew without touching code.
3. **Flask + lightweight JS** (Alpine.js/vanilla via CDN) — keep Donut's no-build ethos.
4. **Hackathon MVP first**, productionise after. Defer the heavier modifiers.

**Why fork rather than extend Donut:** the Donut Toolkit is login-gated, account- and
admin-centric, and scores each survey section independently. The Monkey Puzzle is
no-login, public/viral, open-source, and must collapse a whole submission into a single
categorical persona. ~80% of the *pipeline* is reusable (Flask stack, scoring helpers,
PDF/inline-SVG generation, email reports, multi-step flow, JSON answer persistence), but
the auth/ownership/admin layer is the part to shed. A clean fork reuses the good parts
with zero risk to the three live Donut clients, and can still "tie in" later via shared
data or an API.

## Reuse map (source → target)

Copy and adapt from `/Users/tomspice/Projects/donut-toolkit/`:

| Need | Donut source | Action |
|---|---|---|
| App factory, CSP nonce, security headers | `app/__init__.py` | Copy; drop auth/admin blueprint registration |
| Scoring helpers (`yn`, weighted maps, negative weights, banding) | `app/survey/scoring.py` | Reuse helper style; **replace** per-section banding with a persona-vector classifier |
| PDF + hand-built inline-SVG chart | `app/pdf_utils.py` (`generate_results_pdf`, `_generate_donut_svg`) | Adapt SVG generator into persona card + shareable image |
| Email with PDF attachment | `app/email_utils.py` (`send_certification_email`) | Reuse; make recipient optional (opt-in email copy) |
| JSON answer persistence | `app/models.py` (`SectionResponse.answers` JSON column) | Reuse the "raw answers as JSON, computed result as columns" shape; drop `User`/`Business` ownership |
| Multi-step flow + Jinja survey UI | `app/survey/routes.py`, `templates/survey/section.html` | Reuse structure; drive from data config; add graphical widgets |
| Env-driven config | `config.py` | Copy; strip Railway artifacts |
| Deploy pattern | `deploy/donut.service`, `deploy/nginx.conf`, `deploy.sh.example` | Clone for a new systemd service on the same Infomaniak VPS |

**Strip entirely:** `app/auth/`, all `@login_required`, `User`/`Business`/admin tiers,
`admin/` blueprint, dashboard/ownership routes, TOTP/2FA, password reset.

**Build net-new:** (1) persona classifier, (2) LinkedIn/social share card, (3)
data-driven question loader, (4) graphical front-end widgets.

## Architecture

- **Stack:** Python 3.12 / Flask 3.1 (app-factory + blueprints) / SQLAlchemy 2.0 /
  SQLite (dev) → Postgres (prod) / Alembic / WTForms only where useful / WeasyPrint (PDF)
  / Flask-Mail (optional email) / Bootstrap + Alpine.js via CDN. Mirror Donut so deploy
  and conventions transfer.
- **No accounts.** A submission is anonymous, keyed by a random URL-safe token. Token
  powers the shareable result link, the optional emailed copy, and (later) longitudinal
  "return next year and compare." No PII stored unless the user opts into an email copy.
- **Data-driven content.** A single versioned `content/survey.yaml` defines everything
  Rob/Andrew own; code never hardcodes questions or personas.

### `content/survey.yaml` schema (the contract with Rob/Andrew)

```yaml
meta: { version: 1, title: "The Monkey Puzzle", personas_count: 9 }
personas:                      # the nine outcomes
  accountant:
    name: "The Accountant"
    tagline: "..."
    description: "..."                     # individual wording (default)
    description_organisation: "..."        # optional; organisation-track wording
    natural_allies: [implementer, developer]
    friends:        [communicator]
    necessity:      [activist]              # who this persona most needs
    case_studies: [{title, url}]           # 2-3 curated
    resources:    [{title, url}]
questions:                     # 10-15, ordered
  - id: mission_clarity
    type: spectrum             # spectrum | single | multi | short_text
    prompt: "How clear is your mission?"
    dimension: roots           # Rob's framework axis (see below)
    options:                   # each option carries a persona-weight vector
      - { label: "Crystal clear", weights: { developer: 2, implementer: 1 } }
      - { label: "Still forming", weights: { accountant: 2 } }
scoring:
  method: persona_vector       # sum option weights across personas → argmax
  tie_break: [entrepreneur, connector, ...]   # deterministic order
  # deferred hooks, no-op in MVP:
  equity_modifier: { enabled: false }
  rogers_curve:    { enabled: false }
```

Framework axes to seed placeholder questions from (Rob's notes): **roots** (mission /
vision / team appetite / ecosystem), **requirements** (motivation / knowledge / action
capacity), **comfort–stretch–stress zone**, **strategic domain** (give a platform /
implement / innovate), **footprint vs handprint**, **communication needs**, **role
preference** across the nine profiles.

### Persona classifier (net-new, the core algorithm)

New module `app/survey/persona.py`:
- `score_submission(answers, config) -> dict[persona_id, float]` — sum each chosen
  option's `weights` vector across the nine personas.
- `classify(scores, config) -> PersonaResult` — argmax with deterministic `tie_break`;
  returns the winning persona plus the full nine-dim vector (the "fingerprint").
- Reuse the scoring *helper style* and negative-weight support from Donut's `scoring.py`;
  do **not** reuse its per-section band thresholds.
- Keep the deferred `equity_modifier` / `rogers_curve` as pure functions that transform
  the score vector before `classify` — off in MVP, wired but no-op, so turning them on
  later is a config flip, not a rewrite.

### Graphical output

- Persona card: name, tagline, audience-aware description (`description`/
  `description_organisation`), Natural Allies/Friends/Necessities, 2-3 case studies +
  resources (all from `survey.yaml`).
- **Fingerprint chart:** a radar/spider over the framework axes — the graphical "who."
  Adapt Donut's inline-SVG generator (`pdf_utils.py::_generate_donut_svg`) so the same
  vector renders in the browser, the PDF, and the share image. **Load the `dataviz`
  skill before writing any chart code.**

### Front end (Alpine.js, no build step)

- Widgets: spectrum/slider selector, tap-to-pick single/multi, short-text. Each writes to
  a hidden field consumed server-side, so scoring stays in Python. Progressive
  enhancement — degrades to basic inputs if JS fails.
- One question (or small group) per step with a progress indicator; reuse Donut's
  multi-step flow shape from `survey/routes.py`.

### Sharing (net-new)

- OpenGraph/Twitter meta tags on the result page + a generated share image (persona card
  rendered to PNG/SVG) so the LinkedIn preview is rich.
- LinkedIn share-intent URL, "email me a copy" (reuse `email_utils.py`), and a
  downloadable PDF (reuse `pdf_utils.py`).

## Build phases

**Phase 0 — Scaffold** (`/new-project` pattern): create
`/Users/tomspice/Projects/monkey-puzzle` as its own git repo with `backlog/`, a `dev`
branch, `LICENSE` (it's open-source), and Donut's docs conventions. Carry over Donut's
AI-attribution scrub (gitignore `CLAUDE.md`/`CONTEXT.md`, no `Co-Authored-By` trailers) —
this repo is public-facing.

**Phase 1 — Skeleton + reuse:** port `app/__init__.py`, `config.py`, base templates;
stand up an empty Flask app with security headers; **no auth**. Add anonymous `Submission`
model (token, `answers` JSON, `persona_id`, `score_vector` JSON, timestamps) + first
Alembic migration.

**Phase 2 — Data engine:** write `survey.yaml` loader + schema validation, and a
realistic **placeholder** `survey.yaml` (10-15 questions across Rob's axes, nine personas
with stub allies/case-studies). This proves the schema before real content arrives.

**Phase 3 — Survey flow:** data-driven multi-step routes rendering each question type;
persist answers to the JSON column keyed by token.

**Phase 4 — Persona classifier + result page:** `app/survey/persona.py`, result page with
persona card + radar fingerprint (dataviz skill).

**Phase 5 — Share/output:** OG tags + share image, LinkedIn intent, optional email copy,
PDF download.

**Phase 6 — Deploy:** clone Donut's systemd/nginx pattern as a new service on the
Infomaniak VPS; `dev`-first branch discipline; manual deploy via SSH (read-only server
access — hand deploy steps to Tom, never run mutating server commands).

**Deferred (post-MVP, hooks already stubbed):** equity modifier/coefficient, Rogers-curve
positioning, dual org + individual-manager mode with comparison, annual longitudinal
self-comparison, integrations (Superstruct, GCOP, Arts92, Yourope, European Festival
Roadmap).

## Verification (end-to-end, local)

1. `flask db upgrade && flask run` — app boots with no auth, home renders.
2. Complete the placeholder quiz start→finish in a browser; confirm graphical widgets work
   and degrade gracefully with JS off.
3. Confirm a persona is returned, the radar fingerprint renders, and the card shows the
   right natural allies/friends/necessities/case-studies from `survey.yaml`.
4. Unit tests for `persona.py`: crafted answer sets deterministically yield each of the
   nine personas; tie-break is stable.
5. Edit an option weight in `survey.yaml`, re-run the same answers, confirm the persona
   changes — proves the data-driven contract.
6. Download the PDF; trigger the optional email (Flask-Mail console/MailHog backend) and
   confirm the attachment; check the result page's OG tags render a valid LinkedIn preview.

## Open items for Rob/Andrew (not blocking the build)

- Final 10-15 questions, question types, and per-option persona weight vectors.
- The nine personas' copy, allies/collaborators/friction, and curated case studies.
- Equity-coefficient formula and Rogers-curve thresholds (Phase-2 extension).

Once delivered, these drop into `survey.yaml` — no engine changes expected.

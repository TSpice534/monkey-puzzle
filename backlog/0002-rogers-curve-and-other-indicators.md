---
id: 0002
title: Position respondents on Rogers' innovation curve, plus other indicators
type: feature
status: todo
created: 2026-07-15
branch:
---

## Request
Once the persona itself is decided directly by the 3x3 grid pick (#0001), the rest of
the 11-step survey (everything except step 8) is repurposed rather than removed: it
should position the respondent on Rogers' innovation curve, plus "a couple of other
indicators." Logged as its own backlog item per Tom (2026-07-15) — details (adopter
categories, scoring rules, what the other indicators are) still TBC, largely content
owned by Rob/Andrew.

## Investigation
Docs-first — no new reads beyond what #0001 already covered (`CLAUDE.md`, `CONTEXT.md`,
`app/survey/persona.py`).

- `app/survey/persona.py::apply_modifiers()` (line 51) already has a scaffolded, disabled
  hook for exactly this: `scoring.rogers_curve.enabled` (currently a documented no-op,
  line 61), alongside a similar `equity_modifier` hook. Turning this on and giving it
  real logic is the core of this item.
- Depends on **#0001** landing first: that item repurposes the non-grid questions away
  from persona-scoring, which is the precondition for this item to have data to work
  from. Don't start this until #0001's flow (11 steps, grid at step 8) is in place.
- Where the Rogers'-curve result surfaces (result page, PDF, email copy — all three
  reuse `_persona_card.html` per `CONTEXT.md`) is undecided.
- `Submission` model: `persona_id` / `score_vector` columns exist; a Rogers'-curve
  position (and any "other indicators") likely needs its own field(s) — new
  column(s) + Alembic migration required if so (per `CONTEXT.md`: never add a column
  without one).

## Notes
- Entirely content/design-open at filing time — Rob/Andrew need to define: the adopter
  categories, how the remaining ~10 questions map to a curve position, and what "a
  couple of other indicators" actually are.
- Not blocking #0001 — that item can ship (grid UI + direct persona pick) with this
  logic left as the existing no-op hook.

---
id: 0001
title: Interactive 3x3 grid replaces weighted-scoring persona classifier
type: feature
status: todo
created: 2026-07-15
branch:
---

## Request
Replace the current weighted-scoring persona classifier with a direct-pick mechanism:
two questions rendered as one interactive 3x3 grid.

- x-axis — "Where would you like to act on?": Internal (own organisation and actions) /
  Sector (collaboration and network) / Society (storytelling and speaking out)
- y-axis — "What approach would you like to approve?": Create a stage and address the
  topic / Implement existing solutions / Develop new ideas and ways to progress

3 options per axis = 9 cells, one per persona. The respondent clicks their cell directly
on the grid (not two separate radio questions). Instruction copy depends on audience
(already-built `Submission.audience`): "Find yourself on this grid and select" for
individuals, "Find your organisation on this grid and select" for organisations.

**Confirmed 3x3 → persona mapping** (from Tom, 2026-07-15):

|                  | Internal    | Sector       | Society    |
|------------------|-------------|--------------|------------|
| Develop new ideas and ways to progress | Developer   | Advocate     | Cooperator |
| Implement existing solutions           | Implementer | Entrepreneur | Connector  |
| Create a stage and address the topic   | Documenter  | Communicator | Activist   |

Axis correspondence confirmed by Tom (2026-07-15): x-axis left-to-right = Internal,
Sector, Society; y-axis bottom-to-top = Create a stage and address the topic, Implement
existing solutions, Develop new ideas and ways to progress. Note the y-axis runs
bottom-to-top, the reverse of the order the options were originally listed in — the top
row is "Develop," not "Create a stage."

This **replaces** the existing weighted-scoring classifier (`score_submission` + argmax
in `app/survey/persona.py`) as the mechanism that determines the winning persona. The
remaining question set is repurposed, not removed: it now positions the respondent on
Rogers' innovation curve, plus a couple of other indicators (details TBC with
Rob/Andrew).

**Flow position confirmed by Tom (2026-07-15):** the real survey is 11 steps total, and
the grid is step 8 of 11. This is a smaller step count than the current 16-question
placeholder (`content/survey.yaml`) — the real question set replaces the placeholder
rather than extending it.

## Investigation
Docs-first (CLAUDE.md, CONTEXT.md, docs/PRODUCTION-PLAN.md), confirmed exact names with
targeted greps of `persona.py`, `loader.py`, and the survey templates.

**Files/modules likely touched:**
- `content/survey.yaml` — needs a new top-level construct defining the 3x3 grid: axis
  labels + a 3x3 → persona-id mapping. This is Rob/Andrew-owned content per existing
  convention (`content/survey.yaml` is "the contract with Rob/Andrew" — don't hardcode
  in Python). One existing placeholder question, `strategic_focus` (dimension
  `strategic_domain`), already has options close to the y-axis wording ("Giving others a
  platform" / "Implementing what already works") — worth reusing that dimension name.
  There's no existing axis matching Internal/Sector/Society — net new.
- `app/survey/loader.py` — new schema validation for the grid construct; keep
  `respondent_type_question` / `effective_questions()` audience-routing pattern intact
  for the "Find yourself" vs "Find your organisation" copy switch (same mechanism
  already used for individual/organisation-tagged questions).
- `app/survey/persona.py` — `classify()`/`classify_submission()` (lines ~67, ~83) need a
  new path: the winning persona comes from the grid-cell answer directly, not
  `score_submission`'s argmax over all questions. `apply_modifiers()` (line 51) already
  has the `rogers_curve.enabled` hook (currently a documented no-op, line 61) — this is
  where real Rogers-curve logic gets wired in. Need to decide whether the 9-dim
  "fingerprint" `score_vector` (used by the radar chart) still gets computed from the
  remaining questions, or changes shape now that persona ≠ argmax.
- `app/templates/survey/` — new partial (e.g. `_question_grid.html`) alongside the
  existing per-type partials (`_question_single/_multi/_spectrum/_short_text.html`);
  `step.html` (lines 12-18) picks a partial by `question.type` via `{% include %}` —
  same pattern, add a `grid` branch.
- `app/survey/routes.py` — `step` route currently persists one answer per question id as
  int / list[int] / string (`Submission.answers` JSON). A grid click needs a defined
  answer shape (e.g. `[x_index, y_index]` or the resolved persona id directly).
- `app/models.py` — `Submission.persona_id` / `score_vector` columns already exist and
  may cover this without a migration. If Rogers-curve position needs its own persisted
  field, a new column + Alembic migration is required (CONTEXT.md: never add a column
  without one).

**Open questions only Rob/Andrew/Tom can resolve (not blocking this filing, but should
be resolved before /ship builds this):**
- Whether the radar/fingerprint chart still renders post-grid-pick, and if so what it's
  now a fingerprint *of*, given persona is no longer derived from the score vector.
- Rogers' innovation curve categories/scoring logic, and what "a couple of other
  indicators" means — undefined so far.

## Notes
- **Breaking change to the current classifier**: `classify()`/`classify_submission()`
  currently pick the winning persona via argmax over a weighted score vector built from
  all questions. This item changes that so the grid-cell answer picks the persona
  directly. Confirm with Rob/Andrew whether/how the radar "fingerprint" chart
  (currently rendered from that same score vector) should keep working once persona
  selection no longer depends on it.
- The 3x3 → persona mapping and the axis correspondence are both confirmed by Tom (see
  grid above) — no longer an open question for this item.
- Rogers' innovation curve logic has a scaffolded but disabled hook already:
  `apply_modifiers()`'s `scoring.rogers_curve.enabled` in `app/survey/persona.py` — this
  request is what turns it on. Exact adopter categories / scoring rules and the "couple
  of other indicators" are undefined — flag for Rob/Andrew before implementing that part.
  Recommend `/ship` scopes its first pass to the grid UI + direct persona pick, and
  treats Rogers-curve wiring as a closely related fast-follow once that logic is defined.
- Flow position confirmed: 11 steps total, grid is step 8 of 11 (see grid above) — no
  longer an open question. The real question set is shorter than the current 16-question
  placeholder, so `content/survey.yaml` gets replaced, not extended, when the real
  content lands.

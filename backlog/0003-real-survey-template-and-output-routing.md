---
id: 0003
title: Build real survey content, Output routing, and interactive persona grid (merges #0001)
type: feature
status: todo
created: 2026-07-15
branch:
---

## Request
Build the real 11-step survey from `docs/SURVEY-TEMPLATE.md`, replacing the current
16-question placeholder (`content/survey.yaml`). Scoring in the template is indicative
and still being worked on and may change. The `Output` column dictates what section of
the results page an answer affects:

1. **Innovation-Curve** — where the user sits on the innovation curve and the
   description of their position that's displayed (TBC).
2. **NOW** — a couple of points/sentences describing where the user sits now based on
   their answers.
3. **NEXT** — a couple of points/sentences describing potential next steps based on
   their answers.
4. **Profile (Direct)** — persona/profile grid position (see below).

**Merged in from #0001** (superseded — this item now owns that scope in full): step 8 of
11 is a combined x/y question rendered as one interactive 3x3 grid, not two separate
radio questions, and it's a **direct-pick replacement for the current weighted-scoring
classifier**, not a scored input to it.

- x-axis — "Where would you like to act on?": Internal (own organisation and actions) /
  Sector (collaboration and network) / Society (storytelling and speaking out)
- y-axis — "What approach would you like to approve?": Create a stage and address the
  topic / Implement existing solutions / Develop new ideas and ways to progress

3 options per axis = 9 cells, one per persona. The respondent clicks their cell directly
on the grid. Instruction copy depends on audience (already-built `Submission.audience`):
"Find yourself on this grid and select" for individuals, "Find your organisation on this
grid and select" for organisations.

**Confirmed 3x3 → persona mapping** (from Tom, 2026-07-15):

|                                         | Internal    | Sector       | Society    |
|-----------------------------------------|-------------|--------------|------------|
| Develop new ideas and ways to progress  | Developer   | Advocate     | Cooperator |
| Implement existing solutions            | Implementer | Entrepreneur | Connector  |
| Create a stage and address the topic    | Documenter  | Communicator | Activist   |

Axis correspondence confirmed by Tom (2026-07-15): x-axis left-to-right = Internal,
Sector, Society; y-axis bottom-to-top = Create a stage and address the topic, Implement
existing solutions, Develop new ideas and ways to progress. Note the y-axis runs
bottom-to-top, the reverse of the order the options were originally listed in — the top
row is "Develop," not "Create a stage."

This **replaces** the existing weighted-scoring classifier (`score_submission` + argmax
in `app/survey/persona.py`) as the mechanism that determines the winning persona. The
remaining ~10 questions are repurposed, not removed: they feed Innovation-Curve/NOW/NEXT
(see #0002 for that aggregation logic specifically).

**Grid visual states confirmed by Tom (2026-07-15):**
- **At question time (step 8):** cells are blank — no persona names or hints shown. The
  respondent picks a position purely on the axis meaning, without knowing which persona
  a cell resolves to.
- **On the result page:** the same 3x3 grid renders again, now fully labelled with all 9
  persona names. The respondent's chosen cell/persona is highlighted; the other 8 are
  shown slightly greyed out.

Tom is not yet sure whether the existing radar/fingerprint chart survives alongside this
new grid visualisation, is replaced by it, or both appear — still open, see below.

## Investigation
Docs-first (`CLAUDE.md`, `CONTEXT.md`, `docs/PRODUCTION-PLAN.md`); direct read of
`docs/SURVEY-TEMPLATE.md`; targeted greps to confirm the current schema type enum, the
survey template partials, and a reusable banding pattern in Donut Toolkit.

Read in full, the template confirms:
- **11 rows produce steps** (the router + why + motivation + ambitious + space +
  need-most + have-enough + the combined x/y grid question + topics + support +
  target-groups = 11), with the grid at position **8**, presented as one `Format: Matrix`
  question (score 1-9) — matches the confirmed mapping/axis details above exactly.
- Scores are 1-5 / 1-3 / 1-9 depending on question — indicative and still being worked
  on, so nothing here should be treated as final.

**Files/modules likely touched (for whoever picks this up via /ship):**
- `app/survey/loader.py:10` — `_VALID_TYPES = {'spectrum', 'single', 'multi',
  'short_text'}` doesn't cover a `triangle`-style 3-way force-choice, an exact-N-of-M
  choice constraint, or a 3x3 grid. New types needed (or a `multi` extension with a
  `choose_exactly` field): `Slider` likely maps to the existing `spectrum` type,
  `Button (One Choice)` likely maps to `single`, **`Matrix`** is new (the persona grid —
  needs a 3x3 → persona-id mapping construct plus the audience-aware "Find
  yourself"/"Find your organisation" copy, reusing the existing
  `respondent_type_question` / `effective_questions()` pattern), **`3-way selector
  triangle`** is new (force-choice among 3, used for NOW/NEXT questions), and
  **`8 button (3 choice)`** is new (pick exactly 3 of 8, used for the topics/NOW
  question — not the same as the existing unconstrained `multi` type).
- `content/survey.yaml` — needs a new top-level `output` field per question (one of
  `innovation_curve`/`now`/`next`/`profile_direct`), replacing the current per-option
  `weights`-vector model for every question except the grid, which gets its own 3x3 →
  persona-id mapping construct instead. This is a different scoring shape, not an
  extension of the current one.
- `app/survey/persona.py` — `classify()`/`classify_submission()` (lines ~67, ~83) need a
  new path: the winning persona comes from the grid-cell answer directly, not
  `score_submission`'s argmax over all questions. Need to decide whether the 9-dim
  "fingerprint" `score_vector` (used by the radar chart) still gets computed, or changes
  shape now that persona ≠ argmax. Separately, new aggregation logic per Output category
  is needed for Innovation-Curve/NOW/NEXT — tracked specifically in **#0002**, not this
  item's job to implement, but this item's schema/`output`-field work is what unblocks
  it.
- `app/templates/survey/` — new partial (e.g. `_question_grid.html`) alongside the
  existing per-type partials; `step.html` (lines 12-18) picks a partial by
  `question.type` via `{% include %}` — same pattern, add a `grid` branch (**blank**
  state, question time only). A second, separate rendering — likely a new partial reused
  by `survey/result.html` and possibly `_persona_card.html` — needs a **labelled** state:
  all 9 personas shown, chosen one highlighted, rest greyed out. Two distinct views over
  the same 3x3 layout, not one component with a flag that hides text.
- `app/survey/routes.py` — `step` route currently persists one answer per question id as
  int / list[int] / string (`Submission.answers` JSON). A grid click needs a defined
  answer shape (e.g. `[x_index, y_index]` or the resolved persona id directly).
- `app/models.py` — `Submission.persona_id` / `score_vector` columns already exist and
  may cover the grid without a migration. Innovation-Curve/NOW/NEXT persistence is
  #0002's concern.
- Reuse candidate: Donut Toolkit's `app/survey/scoring.py::_band_range` /
  `section_bands` (5-band score→copy mapping per section) — `CONTEXT.md` says not to
  reuse Donut's *per-section banding for persona classification*, but that constraint is
  moot now that persona is a direct grid pick. Worth flagging to whoever builds #0002:
  this pattern is the right shape for turning a NOW/NEXT numeric score into "a couple of
  points/sentences."

**Open questions only Tom can resolve (not blocking this filing, but should be resolved
before /ship builds this):**
- Whether the radar/fingerprint chart still renders on the result page alongside the new
  labelled 3x3 grid, gets replaced by it, or both appear — Tom's explicitly undecided as
  of 2026-07-15.

## Notes
- **This item supersedes #0001**, which is now marked `wontfix` and points back here —
  don't ship #0001 separately.
- **Breaking change to the current classifier**: `classify()`/`classify_submission()`
  currently pick the winning persona via argmax over a weighted score vector built from
  all questions. This item changes that so the grid-cell answer picks the persona
  directly.
- The 3x3 → persona mapping and the axis correspondence are both confirmed by Tom (see
  grid above) — no longer an open question.
- Flow position confirmed: 11 steps total, grid is step 8 of 11 — no longer an open
  question. The real question set is shorter than the current 16-question placeholder,
  so `content/survey.yaml` gets replaced, not extended.
- Grid visual states confirmed: blank at question time, labelled + chosen-persona
  highlighted + others greyed out on the result page — decided regardless of how the
  open radar-chart question resolves.
- Scoring values in the template (1-5/1-3/1-9) are indicative per Tom and may change —
  don't treat them as final when this gets built.
- Cross-references **#0002** (Rogers'-curve / NOW / NEXT aggregation logic) — that item
  depends on this one landing first (needs the real 11-step flow and the `output` field
  in place) and is deliberately out of this item's scope; leave `apply_modifiers()`'s
  existing no-op hooks in place rather than removing them.

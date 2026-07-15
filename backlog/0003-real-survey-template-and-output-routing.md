---
id: 0003
title: Build real survey content from confirmed template (new formats + Output routing)
type: feature
status: todo
created: 2026-07-15
branch:
---

## Request
The survey template is the question set as it currently stands, with indicative scoring
(scoring is still being worked on and may change) — see `docs/SURVEY-TEMPLATE.md`. The
`Output` column dictates what section of the results page an answer affects:

1. **Innovation-Curve** — where the user sits on the innovation curve and the
   description of their position that's displayed (TBC).
2. **NOW** — a couple of points/sentences describing where the user sits now based on
   their answers.
3. **NEXT** — a couple of points/sentences describing potential next steps based on
   their answers.
4. **Profile (Direct)** — persona/profile grid position (the #0001 grid).

## Investigation
Docs-first (`CLAUDE.md`, `CONTEXT.md`); direct read of `docs/SURVEY-TEMPLATE.md` since
it's the subject of the request; 2 targeted greps to confirm the current schema type
enum and check for a reusable banding pattern in Donut Toolkit.

Read in full, the template confirms:
- **11 rows produce steps** (the router + why + motivation + ambitious + space +
  need-most + have-enough + the combined x/y grid question + topics + support +
  target-groups = 11), with the grid ("Where would you like to act on" / "What approach
  would you like to use") at position **8**, presented as one `Format: Matrix` question
  (score 1-9) — matches what Tom already confirmed for #0001 exactly.
- Scores are 1-5 / 1-3 / 1-9 depending on question — indicative and still being worked
  on, so nothing here should be treated as final.

**Files/modules likely touched (for whoever picks this up via /ship):**
- `app/survey/loader.py:10` — `_VALID_TYPES = {'spectrum', 'single', 'multi',
  'short_text'}` does not cover a `triangle`-style 3-way force-choice or an exact-N-of-M
  choice constraint. Two new types (or a `multi` extension with a `choose_exactly`
  field) are needed before the real template can validate: `Slider` likely maps to the
  existing `spectrum` type, `Button (One Choice)` likely maps to `single`, `Matrix` is
  new (the #0001 grid), `3-way selector triangle` is new (force-choice among 3, used for
  "what do you need most"/NEXT and "what do you already have enough of"/NOW), and
  `8 button (3 choice)` is new (pick exactly 3 of 8, used for the topics/NOW question —
  not the same as the existing unconstrained `multi` type).
- `content/survey.yaml` — needs a new top-level `output` field per question (one of
  `innovation_curve`/`now`/`next`/`profile_direct`), replacing the current per-option
  `weights`-vector model for every question except the grid (#0001 already covers the
  grid's own mapping). This is a different scoring shape, not an extension of the
  current one.
- `app/survey/persona.py` — needs new aggregation logic per Output category (not just
  the existing `score_submission` argmax-over-personas path, which only applies to the
  grid now per #0001). Innovation-Curve position, NOW copy, and NEXT copy each need
  their own resolution logic from their tagged questions' scores.
- Reuse candidate: Donut Toolkit's `app/survey/scoring.py::_band_range` /
  `section_bands` (5-band score→copy mapping per section) — `CONTEXT.md` says not to
  reuse Donut's *per-section banding for persona classification*, but that constraint is
  about persona selection specifically (now moot since #0001 makes persona a direct
  grid pick). A score→banded-copy pattern is exactly the shape needed for turning a
  NOW/NEXT numeric score into "a couple of points/sentences" — worth reusing here.

## Notes
- Cross-references #0001 (grid/Profile mechanism — this template confirms it as one
  combined `Format: Matrix` question, score 1-9, at step 8 of 11, exactly matching what
  was already agreed) and #0002 (Rogers'-curve/"other indicators" — now known to be the
  Innovation-Curve, NOW, and NEXT output sections specifically, not a generic modifier).
- Scoring values in the template (1-5/1-3/1-9) are indicative per Tom and may change —
  don't treat them as final when this gets built.
- `docs/SURVEY-TEMPLATE.md` is currently untracked in git — flagged to Tom, not
  committed as part of this filing (out of scope for a backlog-only change).

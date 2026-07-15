---
id: 0002
title: Position respondents on Rogers' innovation curve (Innovation-Curve only)
type: feature
status: todo
created: 2026-07-15
branch:
---

## Request
Score the 3 Innovation-Curve-tagged questions (`motivation`, `ambition`,
`space_to_progress`) plus a persona-based modifier into a Rogers' innovation-curve
category, and surface it on the result page. Confirmed with Tom (2026-07-15) via
`docs/INNOVATION-SCORING-TEMPLATE.md`:

**Scored questions and their per-option points:**
- **`motivation`** (3 labelled options, but 5 scoring positions — a true slider, not a
  discrete 3-option choice): "I feel the need to act on this topic" = 1, an unlabelled
  "between 1 & 3" stop = 2, "I understand I need to act on this topic (responsibility)"
  = 3, an unlabelled "between 3 & 5" stop = 4, "I act because I understand I have to
  (acceptation)" = 5.
- **`ambition`** (now 5 fully-labelled options, per the updated `docs/SURVEY-TEMPLATE.md`
  — a 5th option, "I want to stay ahead of the curve (advanced)", was added): scores are
  a symmetric curve, **1, 3, 5, 3, 1** in listed order — i.e. the *middle* option
  ("stay ahead of the curve / adopt latest innovative practice") scores highest, both
  extremes ("groundbreaking leader" and "minimal standards") score lowest. This is
  intentional: being maximally bleeding-edge is treated as similarly impractical as
  doing the bare minimum; "practical early adopter" is the sweet spot.
- **`space_to_progress`** (also now 5 options, a new option "I feel comfortable in the
  advancements we are making" inserted as the middle one): same symmetric curve, 1, 3,
  5, 3, 1 — too little space (burned out) and too much unused space (complacent) both
  score low; a good balance scores highest.

**Persona modifier** (added to the 3-question sum): Cooperator +2, Connector +1,
Activist +4, Advocate +2, Entrepreneur +2, Communicator +1, Developer +4, Implementer
+1, **Accountant +0**.

**Total and banding**: sum of the 3 question scores (min 3, max 15) + the persona
modifier (0 to +4) = a total in roughly the 3-19 range, banded via:

| Band | Score range | Colour |
|---|---|---|
| Laggards | 0-2 | Red |
| Late Majority | 3-7 | Amber |
| Early Majority | 8-12 | Yellow |
| Early Adopters | 13-14 | Light Green |
| Innovators | 15-20 | Green |

**Persona rename, bundled into this item**: "Accountant" in the modifier table isn't a
typo — Tom confirmed (2026-07-15) it **replaces "Documenter" across the board**: id,
display name, and copy (tagline/description reworked to an accountant framing —
financial/measurement focus — rather than the current generic "tracking and reporting"
documenter framing), plus every cross-reference to it (other personas' `brethren`/
`besties`/`battlers` lists, the #0003 grid-cell mapping, tests, docs).

**Explicitly out of scope this round** (per Tom, 2026-07-15): NOW and NEXT
aggregation/display. The scoring template only covers Innovation-Curve — NOW/NEXT logic
doesn't exist yet. File a fresh backlog item for NOW/NEXT once that content lands,
rather than guessing at it now (same pattern as the #0001/#0003 merge).

## Investigation
Docs-first (`CLAUDE.md`, `CONTEXT.md`, `docs/INNOVATION-SCORING-TEMPLATE.md`,
`docs/SURVEY-TEMPLATE.md`); confirmed the existing `spectrum` widget's mechanics by
reading `app/templates/survey/_question_spectrum.html` directly.

**Files/modules likely touched:**
- `content/survey.yaml` — `motivation` needs 2 more options added (the unlabelled
  "between" stops, scores 2 and 4); all 3 Innovation-Curve questions' options need an
  explicit per-option score field (new, e.g. `score: <int>` — nothing currently plays
  this role; `weights` is persona-vector-shaped, not a single scalar). Persona rename:
  `documenter:` → `accountant:` in the `personas:` block (id, `name`, reworked
  `tagline`/`description`), plus updating every other persona's `brethren`/`besties`/
  `battlers` list that references `documenter`, plus the grid `cells:` entry
  (`{x: 0, y: 0, persona: documenter}` → `persona: accountant`). New top-level construct
  needed for the persona-modifier table and the banding boundaries (Rob/Andrew-owned
  content, same convention as everything else in this file) — something like an
  `innovation_curve:` key with `persona_modifiers: {...}` and `bands: [...]`.
- `app/survey/loader.py` — validate the new option `score` field (only meaningful on
  `innovation_curve`-output questions, but simplest to allow generically like the
  already-optional `weights`); validate the new `innovation_curve` top-level construct.
- `app/templates/survey/_question_spectrum.html` — **reused as-is, no new widget code.**
  It's already a native `<input type="range">` over `question.options`, submitting a
  0-based index, with a `data-labels` JSON array driving the live label — extending
  `motivation` to 5 options (2 with blank/generic "between" labels) fits this widget
  unchanged. Confirmed by reading the template directly.
- `app/survey/persona.py` — new aggregation function (e.g.
  `resolve_innovation_curve(answers, config, persona_id)`) summing the 3 questions'
  selected-option scores plus the persona modifier, then banding via the boundaries
  table. Reuse candidate flagged in #0003's investigation: Donut Toolkit's
  `app/survey/scoring.py::_band_range`/`section_bands` pattern is the right shape for
  this — a score→band lookup, not the per-section persona-classification pattern
  `CONTEXT.md` warns off (that constraint doesn't apply here).
- `app/models.py` — likely needs a new column (e.g. `innovation_curve_band` string, and
  maybe `innovation_curve_score` int) — `persona_id`/`score_vector` are grid-specific
  per #0003. New Alembic migration required (`CONTEXT.md`: never add a column without
  one).
- Result-page placement is genuinely undecided (flagged already in #0003's own
  investigation, never resolved) — default to an additive card similar in style to the
  labelled persona grid (`_result_grid.html`), showing the band name + colour, unless
  Tom specifies otherwise when this gets `/ship`ped.
- Rename touches: `app/templates/survey/_persona_card.html` (reused by result/PDF/email
  per `CONTEXT.md`) and any place tests assert on `documenter`/`Documenter` —
  `tests/test_persona.py`, `tests/test_real_survey_e2e.py`, `tests/test_grid_flow.py`
  (checks would need repointing to `accountant`), plus `CLAUDE.md`/`CONTEXT.md`/
  `CHANGELOG.md` mentions.

## Notes
- Scoring values are Tom's/Rob-Andrew's and are explicitly still indicative — treat
  `docs/INNOVATION-SCORING-TEMPLATE.md` as the source of truth at build time, not this
  summary, in case it's revised again before `/ship` picks this up.
- Depends on **#0003** having landed (real 11-step flow, grid-direct persona selection)
  — not merged to `dev` yet as of filing, still on
  `feature/real-survey-template-and-output-routing` awaiting Tom's review. This item's
  persona-rename work should happen *after* #0003 merges, to avoid renaming personas on
  a branch that then has to be reconciled with #0003's own branch.
- NOW/NEXT is a known follow-up, not filed yet (no content to build against).

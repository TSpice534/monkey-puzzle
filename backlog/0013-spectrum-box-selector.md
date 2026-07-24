---
id: 0013
title: Replace spectrum slider with click-to-select box row
type: change
status: in-progress
created: 2026-07-24
branch: feature/spectrum-box-selector
---

## Request

Some questions in the survey are currently answered with a slider interface. Change these
to box selections, lined up in a horizontal row across the page. Click to select. For
questions with 5 possible answers, display 5 boxes. For questions with 3 possible answers,
display the 3 boxes across the screen, with small boxes between selections indicating that
selecting there is a mix of the two answers either side.

## Investigation

**Affected questions:** `content/survey.yaml` has exactly 3 `type: spectrum` questions —
`motivation`, `ambition`, `space_to_progress` (all `output: innovation_curve`). All render
today via `app/templates/survey/_question_spectrum.html`, a single `<input type=range>`
with a JS-driven live label (`step.html`'s `{% block scripts %}`, scoped to
`input[type=range][data-labels]`).

**Mapping the request onto real data:** `motivation` already has the "3 real answers + 2
mix answers between" shape described — its options carry `unlabelled: true` on the 2nd/4th
of 5 options (score 2 and 4), used today only to blank the slider's live label. `ambition`
and `space_to_progress` have 5 fully-labelled options and no `unlabelled` flags. So "5
boxes" vs. "3 boxes + 2 small mix boxes between" doesn't need special-casing per question —
render one full box per labelled option and one small "mix" box per `unlabelled: true`
option, positioned between its neighbours. No `survey.yaml` changes needed.

**Reuse, don't invent:** `type: triangle` (`need_most`, `have_enough`, 3-option questions)
already solves this exact problem shape — native radios + `:checked`-sibling CSS (no JS),
one full node per real option plus small secondary "edge midpoint" nodes for the blend
between two flanking options (`app/templates/survey/_question_triangle.html`, backlog
#0010). The edge nodes are small dots with a `visually-hidden` label combining both
flanking option labels for screen readers, styled secondary to the corner nodes
(`.triangle-node--edge` in `app/static/css/theme.css:197`). `_question_single.html` +
`.option-card` (`theme.css:8`) is the plainer reference for "native radio styled as a
clickable card." CLAUDE.md's tech-stack notes confirm this is the house convention —
native HTML/CSS `:checked`-sibling widgets over JS — and the one bit of JS this removes
(the range-slider live label) becomes dead code once there's no `<input type=range>` left.

**What building this touches:**
- `app/templates/survey/_question_spectrum.html` — replace the range input with a
  `role="radiogroup"` row of radio-backed boxes (full box per labelled option, small "mix"
  box per `unlabelled` option between its neighbours), following the triangle widget's
  node/edge split.
- `app/static/css/theme.css` — new `.spectrum-widget` box/row styles (crib sizing/hover/
  checked-state rules from `.option-card` and `.triangle-node`/`.triangle-node--edge`);
  the existing `.spectrum-widget .form-range` rule (`theme.css:33`) goes away.
- `app/templates/survey/step.html` — remove the now-dead range-slider live-label
  `<script>` block (~lines 39-54).
- Backend is untouched: `loader.py`/`routes.py`/`persona.py` already treat a `spectrum`
  answer as a single chosen option index (same as `single`) — confirmed via
  `_VALID_TYPES`/`_TYPES_WITH_OPTIONS` in `loader.py` and the comment at `routes.py:73`.
  A radio value instead of a range value needs no schema change.
- Tests referencing slider-specific markup/behaviour need updating, not just extending:
  `tests/test_real_survey_e2e.py` (`test_motivation_slider_unlabelled_stop_label_text_is_not_rendered`,
  `test_motivation_slider_accepts_all_five_positions`, ~lines 356-456) and
  `tests/test_innovation_curve_verification.py` (~lines 10, 127).

## Notes

- Exact visual size/shape of the "mix" boxes (small square vs. dot, à la the triangle
  widget's edge nodes) — left to build time, following the triangle precedent.
- Whether full-size boxes wrap on narrow/mobile viewports or stay a single scrollable row —
  Tom said "horizontal row across the page"; mobile behaviour left to work out at build time.

---
id: 0014
title: Topics question (Q9) — allow choosing up to 3, not exactly 3
type: change
status: in-progress
created: 2026-07-24
branch: feature/topics-question-choose-up-to-3
---

## Request
Question 9 ("What three topics do you like to focus on the most?") currently forces
respondents to pick exactly 3 options. Change it so respondents can choose up to 3
(minimum 1, maximum 3). Reword the prompt and add an instructional line above the
options reading "Choose up to 3 options."

Suggested prompt rewording: "Which topics do you like to focus on the most?"
(drops "three" now that the count is flexible).

## Investigation
- `content/survey.yaml:313-327` — the `topics` question, currently
  `type: multi_exact` / `choose_exactly: 3`.
- `app/survey/loader.py:205-215` — validates `multi_exact`'s `choose_exactly` field.
  Needs a new validated field for a range (e.g. `choose_min`/`choose_max`, or a
  `choose_up_to: N` shorthand meaning 1..N) — decide the schema key when scoping in
  `/ship`.
- `app/survey/routes.py:131-140` — block-advance guard currently checks
  `len(value) == choose_exactly`; needs to become a range check
  (`choose_min <= len(value) <= choose_max`) with an updated flash message (currently
  "Please select exactly {n} option{s}.").
- `app/templates/survey/_question_multi.html` — shared by `multi`/`multi_exact`; needs
  the new instructional line ("Choose up to 3 options.") rendered above the option
  cards when a max-but-not-exact count applies. Check whether this should be a new
  optional `instructions` field like `profile_grid` already has (`content/survey.yaml`
  around line 287) rather than a hardcoded string, so wording stays data-driven.
- `app/survey/persona.py::resolve_now_next` (lines 190-202) — already degrades
  gracefully to a skipped "Now" statement if the answer list is empty; moot once a
  minimum of 1 is enforced, but worth a test case confirming the min is actually
  enforced (mirror `tests/test_grid_flow.py::test_multi_exact_wrong_count_rerenders_without_advancing`).
- Whichever schema key is chosen, decide whether to generalize the existing
  `multi_exact` type (e.g. it now accepts either `choose_exactly` or a min/max pair) or
  add a distinct type — this repo's convention (`_VALID_TYPES` in loader.py) currently
  treats `multi`/`multi_exact` as the only two multi-select variants, both sharing one
  template.

## Notes
- Confirmed with Tom (2026-07-24): minimum is 1, not 0 — "choose up to 3" reads as 1-3
  in the UI copy, but at least one topic must be picked to advance, so the "Now"
  narrative statement always has content.
- Test coverage to extend: `tests/test_grid_flow.py` (multi_exact count-validation
  tests), `tests/test_loader.py` (schema validation tests), and
  `tests/test_real_survey_e2e.py:213` (already references step 9 / `topics` /
  `choose_exactly: 3` directly — will need updating regardless of schema key chosen).

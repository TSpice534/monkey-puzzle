---
id: 0015
title: Reword "why" question, move to end of survey, show answer on results + PDF
type: change
status: todo
created: 2026-08-04
branch:
---

## Request

Change question 2 — "Do you have a \"why\"? A reason why this topic is relevant or
important for you?" — to "In one sentence, why is this work on this topic important to
you?" and move it to the end of the survey. Include the answer to this question on the
results page and in the PDF reports.

## Investigation

From project CLAUDE.md plus targeted greps (survey.yaml, loader/routes/persona,
tests):

- `why_reason` is currently question 2 in `content/survey.yaml` (~line 228), right
  after the `respondent_type` router. Already `type: short_text` (free-text), no
  options, no `output:` tag; `persona.py::score_submission` skips `short_text`, so
  nothing scores off it.
- The answer is already persisted in `Submission.answers['why_reason']` (trimmed;
  empty allowed — the question is skippable). No model change, no migration.
- **Reword:** edit the `prompt:` string in `survey.yaml`.
- **Move to end:** question order is positional in `questions:` — move the block
  after `target_groups` (currently last). Router stays first; nothing else depends
  on `why_reason`'s position. Update the hardcoded step index
  `tests/test_persona_copy_verification.py::STEP_WHY_REASON`; the `step/4` posts in
  `test_survey_routes.py` use the small fixtures, unaffected.
- **Display on results + PDF:** follow the Now/Next pattern (backlog #0007) — derive
  at render time from `Submission.answers`, no new column. Add a context builder in
  `app/survey/routes.py` (alongside `_now_next_context`) and render via
  `_persona_card.html` or a new `_result_why.html` shared partial — that card is
  shared verbatim by web `result.html` and `pdf/result.html`, so one inclusion covers
  both requested surfaces. Email was not requested — leave it out, consistent with
  existing email gaps left as-is.
- **Edge cases:** guard on empty/absent answer (skippable question, old submissions).
  User free text — rely on Jinja auto-escaping, no `| safe` (same rule as Now/Next).

## Notes

- Open design choice for the planner: key the display off the hardcoded `why_reason`
  question id, or add a loader-validated `output: why` tag like `now`/`next`. Either
  works; the tag route matches the existing pattern but touches the loader + its
  validation tests.
- Remember the CHANGELOG.md `Unreleased` bullet on completion (repo rule).

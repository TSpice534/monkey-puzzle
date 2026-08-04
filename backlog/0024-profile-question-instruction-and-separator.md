---
id: 0024
title: Instruction line + visual separator on the combined profile step (Question 7)
type: change
status: todo
created: 2026-08-04
branch:
---

## Request
On the combined profile step (Question 7 — "Finish the following sentence..."):
- Add an instruction under the prompt saying "Select one option from the top AND bottom row"
- Add a visual separator between the top row (approach options) and bottom row (scope options)

## Investigation
Confirmed "Question 7" is the combined profile step (`profile_approach` + `profile_scope`,
collapsed into one rendered step by `app/survey/loader.py::survey_steps`, backlog #0017 Part
B). Survey step order: 1 respondent_type, 2 motivation, 3 ambition, 4 space_to_progress,
5 need_most, 6 have_enough, **7 profile pair (combined)**, 8 topics, 9 support_type,
10 target_groups, 11 why_reason.

Two precedents already exist in the codebase for optional, survey.yaml-driven instruction
text rendered as muted small text:
- `question.instructions` (used by `multi_range`/`topics`) — rendered in
  `app/templates/survey/_question_multi.html` as `<p class="text-muted small mb-2">`.
- `question.explanation` — rendered in `step.html` as
  `<p class="question-explanation text-muted small mb-3">`.

Recommended approach:
- Add an optional `profile_matrix.instructions` field in `content/survey.yaml`, set to
  "Select one option from the top AND bottom row".
- Validate it in `app/survey/loader.py::_validate_profile_matrix`, same shape as the existing
  optional `sentence_stem_organisation` field (non-empty string if present, else absent is
  fine).
- Pass it through in `app/survey/routes.py::_render_step` (`combined_profile` branch) as
  `profile_instructions=matrix.get('instructions')`.
- Render it at the top of `app/templates/survey/_question_profile_pair.html` (before the live
  sentence paragraph), reusing the `text-muted small` treatment from `_question_multi.html`.
- For the separator: no existing divider component/CSS class in `theme.css` — the codebase
  leans on plain Bootstrap 5.3 utilities elsewhere, so add a plain
  `<hr class="my-4" aria-hidden="true">` between the two `role="radiogroup"` row `<div>`s in
  `_question_profile_pair.html` (`aria-hidden` since it's decorative and both radiogroups
  already carry their own `aria-label`).

Files likely touched: `content/survey.yaml`, `app/survey/loader.py`,
`app/survey/routes.py`, `app/templates/survey/_question_profile_pair.html`,
`tests/test_loader.py` (extend existing `profile_matrix` validation coverage).

## Notes
No open questions — small, well-precedented change, fully scoped from docs + existing code
patterns (no source read beyond confirming the pattern).

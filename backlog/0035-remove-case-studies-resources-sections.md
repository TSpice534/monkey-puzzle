---
id: 0035
title: Remove Case Studies / Resources sections from result page
type: change
status: todo
created: 2026-09-23
branch:
---

## Request

Remove from results page:
- Case studies section and placeholder link
- Resources section and placeholder link

## Investigation

Source: `CLAUDE.md` already flags these as Phase-2 placeholders ("`case_studies`/
`resources` remain Phase-2 placeholders, out of scope"), confirmed by reading the actual
render partial.

- **Single render site**: `app/templates/survey/_persona_card.html:42-62` — two `{% if
  persona.case_studies %}` / `{% if persona.resources %}` blocks, each a heading + `<ul>`
  of links (`cs.url`/`cs.title`, `r.url`/`r.title`). This partial is the *only* place
  either section renders.
- **Shared across two surfaces**: `_persona_card.html` is included by both
  `app/templates/survey/result.html:26` (the live web result page) and
  `app/templates/pdf/result.html:43` (the downloadable/emailed PDF) — removing the two
  blocks here removes the sections from both surfaces in one edit. The email body itself
  (`app/templates/email/result.html`/`result.txt`) doesn't render the persona card
  directly — per `CLAUDE.md`, email just attaches the generated PDF — so there's no third
  template to touch.
- **Data stays put**: `content/survey.yaml` still holds `case_studies`/`resources` on
  every persona (all "Placeholder case study —"/"Placeholder resource —" entries), and
  `app/survey/loader.py:101,539-540` still validates/defaults those fields. This request
  only asks to remove the *section from the results page* — the underlying yaml fields
  can stay (they're harmless if unrendered, and Rob/Andrew may still fill them in later
  per the Phase-2 note). Stripping the yaml/loader schema too would be a separate, broader
  cleanup — flagged as optional below, not part of this request.
- **Tests unaffected**: grepped `tests/` for `case_studies`/`resources` — the hits
  (`test_loader.py`, `test_real_survey_e2e.py`, `test_survey_explanation_rendering.py`,
  `test_innovation_curve_visualisation_verification.py`) all test the yaml
  loader/schema/fixtures (e.g. `accountant['case_studies'] == []`), not the removed
  template markup. No test assertions reference the "Case studies"/"Resources" headings
  or rendered links, so no test changes are expected — `/ship`'s tester stage should
  confirm this rather than assume it.

## Notes

- Small, single-file, mechanical change (delete two `{% if %}` blocks from one shared
  partial) — no design decision left open, follows no new pattern. Looks like a
  `/quick-ship` candidate rather than the full pipeline.
- Optional follow-up (not in scope here): if Tom wants the placeholder `case_studies`/
  `resources` data removed from `content/survey.yaml` too (now fully unrendered), that'd
  be a separate small item — left out since the request only mentioned the results page.

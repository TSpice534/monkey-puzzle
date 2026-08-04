---
id: 0019
title: Add prompt_organisation schema field for org-register question prompts
type: feature
status: in-progress
created: 2026-08-04
branch: feature/prompt-organisation-field
---

## Request

Filed as a follow-up from backlog #0017 Part B (profile question redesign). Some
questions in `docs/SURVEY-TEMPLATE.md` show a distinct organisation-register prompt
(e.g. "Complete the following sentence: 'We want to...'") alongside the individual-
register prompt ("...'I want to...'"). The survey schema currently has no per-question
`prompt_organisation` field — only `label_organisation` on options and
`description_organisation` on personas support an audience-specific variant. Prompts
themselves are single-wording only, so the organisation-register phrasing from the
template is currently dropped and the individual-register prompt is shown to both
audiences.

## Notes

- Surfaced while building #0017 Part B (the profile_grid → two single-select questions
  replacement): its Row 1 prompt has an org-register variant in the template
  ("We want to...") with no schema field to hold it. Part B shipped using the single
  individual-register prompt for both tracks per Tom's explicit call — this item is
  the proper fix, not blocking.
- Scope: add `prompt_organisation` (optional string) to the question schema/loader,
  wire it into whichever template renders the prompt (`step.html`), and decide which
  existing questions besides the Part B rows would actually use it — check
  `docs/SURVEY-TEMPLATE.md` broadly rather than just the one question that surfaced
  this, in case other questions have the same latent gap.
- Not yet investigated in depth — this is a plan-mode candidate for `/request` proper,
  or hand straight to `/ship`'s planner stage to investigate at build time.

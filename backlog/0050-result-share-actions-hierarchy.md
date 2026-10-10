---
id: 0050
title: Result page: one primary share action, others secondary
type: change
status: shipped
created: 2026-10-10
branch: feature/batch-result-page-polish
---

## Request
All share actions are grey outline buttons and 'Email me a copy' is a filled grey that reads as disabled. Make 'Share on LinkedIn' the primary action and make the rest clearly secondary.

## Investigation
`app/templates/survey/result.html` lines ~35-70 (`btn-outline-secondary`, `btn-secondary`). Use the unified brand button (see the button-green item). Keep 44px targets (DESIGN.md rule 4). apple-design `buttons.md`: use a prominent style for the most likely action.

## Notes
Route: `/ship` (or `/quick-ship` after the button-green item lands). Depends on the unify-primary-button-green item.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

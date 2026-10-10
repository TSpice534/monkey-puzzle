---
id: 0046
title: Unify primary button green with brand-primary
type: change
status: todo
created: 2026-10-10
branch:
---

## Request
Primary buttons (Begin, Next) render Bootstrap `btn-success` #198754, while the selected grid cell, icons and share card use `#2e7d32`. Pick one and use it everywhere.

## Investigation
Measured in the running app: Begin is rgb(25,135,84). Override `btn-success` (or add a `btn-brand` variant) in `app/static/css/theme.css` using `--brand-primary` / `--brand-primary-dark`, with a dark-appearance value. White on #2e7d32 is 5.13:1, so contrast is fine. Check hover, focus and disabled states.

## Notes
Route: `/quick-ship`. Related: DESIGN.md rule 6 and the 'Two greens' known gap.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

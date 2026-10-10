---
id: 0052
title: Pressed states and text-wrap polish
type: change
status: shipped
created: 2026-10-10
branch: feature/batch-result-page-polish
---

## Request
Add `:active` feedback (scale 0.98) to option cards and buttons, and `text-wrap: balance` on headings and `pretty` on body text.

## Investigation
`app/static/css/theme.css`. Gate the press animation with `prefers-reduced-motion: no-preference` (DESIGN.md rule 7). Result taglines currently strand single words on a line on mobile.

## Notes
Route: `/quick-ship`.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

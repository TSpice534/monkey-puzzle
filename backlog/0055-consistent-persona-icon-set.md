---
id: 0055
title: Replace placeholder persona icons with a consistent set
type: change
status: todo
created: 2026-10-10
branch:
---

## Request
The nine persona icons mix filled and outline styles and uneven visual weight. Replace them with one consistent set, or commission illustrations.

## Investigation
Icons: `app/static/icons/*.svg`, inlined by `app/survey/icons.py`; styled by `.persona-icon*` in theme.css. Backlog #0005 shipped these explicitly as placeholders. Options: Phosphor or Tabler, copied in as inline SVG (no build step, MIT licence), or a real illustration set. Icons must keep their `aria-hidden` handling and metaphor-per-persona mapping.

## Notes
Route: `/ship`. Open question for Tom, Rob and Andrew: library icons or commissioned illustration.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

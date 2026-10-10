---
id: 0054
title: Certificate hardcodes tomspice.co.uk/monkey-puzzle
type: change
status: todo
created: 2026-10-10
branch:
---

## Request
The certificate PNG prints the text `tomspice.co.uk/monkey-puzzle` regardless of environment. Make it come from config.

## Investigation
`app/survey/charts.py` line 107, `<text ...>tomspice.co.uk/monkey-puzzle</text>`. Move to config (e.g. a `PUBLIC_URL` setting) and use it in the share caption too if not already. Remember the asset cache key.

## Notes
Route: `/quick-ship`. Open question: what the public URL should be in production (confirm with Tom).

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

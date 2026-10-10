---
id: 0049
title: Result page: make the persona card the hero
type: change
status: shipped
created: 2026-10-10
branch: feature/batch-result-page-polish
---

## Request
The persona card carries the same visual weight as the four cards below it, with a 24px icon. Make it the page's hero moment and quieten the rest.

## Investigation
Files: `app/templates/survey/_persona_card.html`, `result.html`, `app/static/css/theme.css` (`.persona-icon--card`). Suggested: ~64px icon, larger name, tinted background using `--selected-tint`; drop borders on the lower cards and group with spacing. Must still work in dark appearance and in the PDF (`pdf/result.html`) and email copy, which do not inherit theme.css.

## Notes
Route: `/ship` with the design pass on. Do not change persona copy or colours (content in `content/survey.yaml`). Related findings from the 2026-10-10 review; see DESIGN.md.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

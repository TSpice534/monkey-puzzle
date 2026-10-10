---
id: 0051
title: Innovation curve: highlighted bar and legend visibility
type: change
status: in-progress
created: 2026-10-10
branch: feature/batch-result-page-polish
---

## Request
Highlighted bars in the pale bands (yellow 1.66:1, light green 2.50:1, amber 2.85:1 vs white) can be near-invisible, and the legend wraps awkwardly on mobile ('Laggards' alone on a row).

## Investigation
Chart is `render_innovation_curve_svg` in `app/survey/charts.py` plus `_result_innovation.html` (card has a 6px left border in the band colour). Suggest a thin dark outline on the highlighted bar and card border, and a CSS grid legend. Do not change band colours: they live in `content/survey.yaml` and belong to Rob and Andrew.

## Notes
Route: `/ship`. Colour changes (darker bands) would need Rob and Andrew's agreement; propose separately.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

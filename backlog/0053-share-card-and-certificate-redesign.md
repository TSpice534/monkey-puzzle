---
id: 0053
title: Redesign share card and certificate
type: change
status: todo
created: 2026-10-10
branch:
---

## Request
The 1200x630 share card and the 1200x1200 certificate are text on off-white with a green edge. Add the persona icon and a band-coloured accent so they read as Monkey Puzzle when posted.

## Investigation
`render_share_card_svg` and `render_certificate_svg` in `app/survey/charts.py`, rasterised by cairosvg and cached by `app/asset_cache.py` (content-addressed, so a changed template must bust the cache). Persona icons are in `app/static/icons/` and `app/survey/icons.py`. Check text contrast on the yellow and light-green bands (DESIGN.md known gaps).

## Notes
Route: `/ship`, multi-surface check (web, PDF, email, share, certificate). Depends on the consistent-icon-set item if that is done first.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

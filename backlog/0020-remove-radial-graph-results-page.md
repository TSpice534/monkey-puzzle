---
id: 0020
title: Remove radial graph from results page
type: change
status: todo
created: 2026-08-04
branch:
---

## Request
Remove the radial (radar/fingerprint) graph from the results page.

## Investigation
Docs-first + targeted code read (monkey-puzzle/CLAUDE.md, routes.py, charts.py,
result.html — no open-ended tour needed).

- The chart is `render_fingerprint_svg()` in `app/survey/charts.py`, called separately
  in three places: the web results page (`routes.py::result()`), the PDF download
  (`download_pdf()`), and the emailed PDF copy (`email_result()`). The share/OG image
  (`share_image()`) uses a different function, `render_share_card_svg`, which nests its
  own internal call to the same chart.
- Scope is the **web results page only**: drop `{{ fingerprint_svg | safe }}` from
  `app/templates/survey/result.html` (line 27) and the matching `fingerprint_svg`
  computation/kwarg in `routes.py::result()` (lines 286, 296).
- Confirmed the 3x3 persona grid, persona card, innovation-curve card, and Now/Next
  statements are all independent of the fingerprint chart and unaffected.
- PDF, emailed copy, and the share-card PNG are untouched — not mentioned in the
  request, and each has its own independent call site.

## Notes
None — scope is unambiguous from "results page."

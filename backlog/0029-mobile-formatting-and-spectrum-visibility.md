---
id: 0029
title: Innovation-curve label overlap + spectrum question options not visible on mobile
type: bug
status: shipped
created: 2026-08-30
branch: feature/mobile-formatting-and-spectrum-visibility
---

## Request
Tom did a visual pass on mobile and desktop: label text is "smushing" on the Your
Sustainability Who result page (named example: "Innovator" overlapping on the innovation
curve), there are other minor formatting errors on the web version, and the response
options for Questions 2, 3 & 4 aren't visible at all.

## Investigation
Two confirmed, distinct root causes (both found via read-only code investigation, not
reproduced live):

**1. Innovation-curve label overlap** — app/survey/charts.py::render_innovation_curve_svg()
(lines 49-157) computes label font-size from overall SVG width only and centers each band
name over its bar span with no width-awareness, wrapping, or truncation. Backlog #0012
shrank the Innovators band to a single bar (1/16 of the width) — its label is now far wider
than its span, overlapping "Early Adopters". This happens at any viewport size (it's SVG
coordinate math, not CSS). Additionally the SVG has fixed width="640" height="240" with no
`max-width:100%; height:auto` rule anywhere in app/static/css/theme.css, so it also
clips/overflows on narrow mobile screens.

**2. Spectrum question (Q2 motivation, Q3 ambition, Q4 space_to_progress) options not
visible** — app/static/css/theme.css:37-70 (.spectrum-widget/.spectrum-node) lays out 5
option boxes as flex with no min-width and no flex-wrap. On narrow viewports the boxes
compress until sentence-length labels overlap/overflow badly. Backlog #0013 (which built
this widget) explicitly flagged mobile wrapping as unresolved in its own Notes and it was
never followed up — confirmed via `grep -rn "@media" app/static app/templates` returning
zero matches anywhere in the app.

Both trace to the same gap: no responsive/mobile CSS exists anywhere in the app.
.triangle-widget/.grid-cell (same file) may share this gap but weren't reported broken —
worth a quick check at build time, not chasing speculatively here.

## Notes
- Fix for #1 is structural (label-width-aware logic in the SVG generator), not just CSS —
  needs font-size shrink, truncation, or offset logic for narrow single-bar bands, plus a
  responsive sizing rule for the SVG container.
- Fix for #2 is a CSS breakpoint: flex-wrap + min-width per box, or a stacked layout below a
  width threshold.
- Tom's "computer... minor formatting errors" is vaguer than the two items above and wasn't
  reproducible from static analysis — check for it alongside the two confirmed fixes rather
  than as a separate line item.
- Recommend testing on an actual narrow mobile viewport (browser devtools responsive mode at
  ~375px width is enough) before marking this shipped, since neither root cause was
  reproduced live.

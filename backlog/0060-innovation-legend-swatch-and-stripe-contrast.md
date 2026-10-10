---
id: 0060
title: Check whether pale legend swatches, band dot and card stripe need outlines
type: change
status: todo
created: 2026-10-10
branch:
---

## Request
After #0051 the highlighted bar is outlined, but the legend swatches, the band-name dot and the card's 6px left stripe still use the band colours without an outline (yellow 1.66:1, light green 2.50:1, amber 2.85:1 against white). Decide whether that is acceptable now and, if not, outline them.

## Investigation
`app/templates/survey/_result_innovation.html` (swatches `.curve-legend-swatch`, dot, inline `border-left: 6px solid`), `app/static/css/theme.css`, `app/templates/pdf/result.html`. The band name is always shown as text beside each, so meaning survives; this is about non-text contrast (WCAG 1.4.11). Darker band colours would solve it at the source but belong to Rob and Andrew (`content/survey.yaml`). The legend's row gap on tablet and desktop is now 0.5rem where it was 1rem; the CSS comment says "same look as before", which is not quite true; fix the comment or the gap.

## Notes
Raised by the #0051 reviewer (follow-ups, all Low). This is a check item: Tom looks at the result page first and may close it as acceptable. Route: `/quick-ship` if wanted.

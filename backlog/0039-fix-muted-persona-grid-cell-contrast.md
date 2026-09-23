---
id: 0039
title: Fix low-contrast text on muted result-page persona grid cells
type: bug
status: shipped
created: 2026-09-23
branch: quickship/fix-muted-grid-cell-contrast
---

## Request

The result page's 3x3 position grid (`_result_grid.html`) renders the 6 non-selected personas'
names in `.grid-cell--muted` (`app/static/css/theme.css:160-164`): `color: #ced4da` on the card's
white background, further dimmed by `opacity: 0.7` on the whole cell. Computed WCAG contrast of
`#ced4da` on white alone is ~1.49:1 — the added opacity only lowers it further. This is real,
readable persona-name text (`_result_grid.html:44`, `{{ cell_persona.name }}`), not decoration,
and needs to meet the 4.5:1 minimum for body-size text.

Fix: pick a muted color in the `#6c757d`-`#495057` range (the grid's own header text,
`.persona-grid th`, already uses `#495057` at ~8.2:1 and reads fine as "de-emphasized but
legible") and drop the extra `opacity: 0.7`, which does nothing but subtract contrast once the
text color itself is already muted enough to read as non-selected.

## Investigation

Sourced from an `apple-design` skill HIG-grounded review of the live app (screenshots +
`theme.css`/template reads), not a fresh investigation — see the full review earlier in this
session for the contrast math and citations (`accessibility.md › Vision`, 4.5:1 minimum).

Files touched: `app/static/css/theme.css` (`.grid-cell--muted`, lines ~160-164). No template or
Python changes expected — this is a pure color-value fix. Also affects the mobile grid at
`.persona-grid` under the `@media (max-width: 767.98px)` block (theme.css:426-434), which shrinks
the same muted cells to 0.75rem — same fix applies, no separate mobile rule needed.

## Notes

Also re-check `.persona-icon--grid` (theme.css:278-281) — it inherits `currentColor` from the
muted cell, so the icon in each non-selected cell is exactly as low-contrast today and will
brighten automatically once the text color is fixed; no separate icon-color change needed.

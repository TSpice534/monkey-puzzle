---
id: 0040
title: Innovation-curve chart band labels can shrink below legible size
type: bug
status: shipped
created: 2026-09-23
branch: feature/innovation-curve-chart-label-legibility
---

## Request

`render_innovation_curve_svg` (`app/survey/charts.py`) lays out the bell-chart's band-name
labels with a shrink-to-fit pass floored at `_LABEL_MIN_FONT_SIZE = 8.0` SVG units
(`charts.py:115`), inside a 640x240 viewBox. `theme.css:389-392` then scales the whole `<svg>`
down responsively (`max-width: 100%; height: auto`) to fit its card — on a phone-width result
page that's roughly a 640->340px scale, so an 8-unit label can render close to 4px on screen.
Confirmed on a live 390px-viewport screenshot: the "Innovators / Early Adopters / Early Majority
/ Late Majority / Laggards" labels under the chart are barely legible.

This text is also SVG `<text>` with a hardcoded `font-size` attribute — it doesn't respond to a
browser's text-size/zoom accessibility setting the way normal HTML text does, unlike everything
else in the app.

Fix direction (needs a design call at ship time, not fixed here): either raise
`_LABEL_MIN_FONT_SIZE` and accept some label collision/wrapping instead of shrinking further, cap
how far the SVG is allowed to scale down before switching to a narrower/stacked chart layout, or
move the band-name labels out of the SVG into an HTML legend below the chart (same pattern
already used for the grid-relationship legend in `_result_grid.html`) so they inherit normal text
scaling.

## Investigation

Sourced from an `apple-design` skill HIG-grounded review (live screenshots at desktop 1280px and
mobile 390px viewports, plus a `charts.py` read) — see the full review earlier in this session
(`typography.md › Ensuring legibility`, `accessibility.md › Vision` — "give people the option to
enlarge text").

Files touched: `app/survey/charts.py` (`render_innovation_curve_svg`, `_layout_band_labels`,
`_LABEL_MIN_FONT_SIZE`), possibly `theme.css:389-392` if the fix caps scaling rather than
reflowing, possibly a new HTML legend partial if labels move out of the SVG.

## Notes

Worth spot-checking `render_fingerprint_svg` (the radar chart) and `render_share_card_svg`/
`render_certificate_svg` for the same fixed-SVG-font-size pattern while in this code, though only
the innovation-curve chart's labels were confirmed illegible on the mobile screenshot in this
review.

**Shipped:** `render_fingerprint_svg` doesn't exist — it was deleted by backlog #0025 before this
item was filed, so the spot-check above doesn't apply to it. `render_share_card_svg`/
`render_certificate_svg` were also checked and left alone: both are rasterised to fixed-size PNGs
by cairosvg and never responsively downscaled as live browser text, so their fixed `font-size`
pattern is correct as-is. Fix direction chosen: moved the band-name labels out of the SVG into an
HTML `curve-legend` below the chart (`_result_innovation.html`), not a font-size floor raise or a
scale cap — see `.pipeline/spec.md` on the `feature/innovation-curve-chart-label-legibility`
branch for the full rationale (the shrink-to-fit floor is never reached at real render sizes, so
raising it would have been a no-op).

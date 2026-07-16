---
id: 0011
title: Innovation-curve visualisation on results page
type: feature
status: in-progress
created: 2026-07-16
branch: feature/innovation-curve-visualisation
---

## Request
On the results page, add a visualisation of the innovation curve and the respondent's
position on it. A reference image of the curve is in `docs/Diffusion_of_ideas.svg`.

Two levels of visual division:
1. The curve's five sections (Innovators, Early Adopters, Early Majority, Late Majority,
   Laggards) coloured using the colours already defined in the scoring templates.
2. Within that, divide the curve into 21 bars — one per score point, 0–20. Show the
   respondent's position by highlighting the bar for their score and reducing saturation
   on all the other bars.

## Investigation

**Existing feature this extends (backlog #0002/#0004):** the innovation-curve score/band
is already computed and stored (`Submission.innovation_band`/`innovation_score`,
`app/survey/persona.py::resolve_innovation_curve`) and shown today as a plain text/colour
card — `app/templates/survey/_result_innovation.html`, a shared partial included on both
the web result page (`survey/result.html:34`) and the PDF (`pdf/result.html:68`). Email
does **not** include this partial (renders its own inline markup instead) — established
precedent, not something this request should change.

**Band data (colours + boundaries), from `content/survey.yaml`'s `innovation_curve.bands`,
confirmed against `docs/INNOVATION-SCORING-TEMPLATE.md`:**
| Band | Score range | Colour |
|---|---|---|
| Laggards | 0–2 | `#c0392b` (red) |
| Late Majority | 3–7 | `#e67e22` (amber) |
| Early Majority | 8–12 | `#f1c40f` (yellow) |
| Early Adopters | 13–14 | `#7cb342` (light green) |
| Innovators | 15–20 | `#2e7d32` (green) |

Score is a single int 0–20 (21 discrete points) — matches "one bar per score point,
0–20" exactly. `INNOVATION-SCORING-TEMPLATE.md`'s "Grouping" table also gives each band's
adoption-population % (16 / 34 / 34 / 13.5 / 2.5) — the classic Rogers bell-curve
proportions. Useful if the curve should visually bulge to match `Diffusion_of_ideas.svg`
rather than render as a flat bar strip; flagged as an open question below rather than
decided here.

**Rendering pattern to reuse — inline SVG, not JS/canvas:** `app/survey/charts.py`
already has two hand-built inline-SVG generators (`render_fingerprint_svg`,
`render_share_card_svg`), explicitly modelled on Donut Toolkit's SVG approach so charts
render with no external assets/JS (CSP-safe, and WeasyPrint-safe for the PDF surface).
The wiring pattern in `app/survey/routes.py`: a `*_svg` string is built server-side per
request (e.g. `fingerprint_svg = render_fingerprint_svg(...)` appears at routes.py:192,
232, 261 — once each for the web `result()`, `download_pdf()`, and `email_result()`
views) and passed into the template context, then embedded unescaped via
`{{ fingerprint_svg | safe }}`. The new visualisation should follow this exact pattern:
a new `render_innovation_curve_svg(score, bands)`-style function in `charts.py`, called
from `routes.py` alongside the existing `fingerprint_svg` calls (web + PDF only, per the
email exclusion noted above), and embedded inside `_result_innovation.html`.

**Context-building gap:** `routes.py::_innovation_context` (routes.py:67-83) currently
only resolves the *matched* band (name/colour/tagline/description for the respondent's
own band) — it does not currently expose the full `bands` list to the template, which
the new visualisation needs (to draw all 5 sections, not just the respondent's own).
Either extend `_innovation_context`'s return dict with the full bands list + a
pre-rendered `curve_svg` string, or build the SVG separately in `routes.py` alongside
`fingerprint_svg` and pass it as its own context key — same call-site shape either way.

**Saturation/highlight mechanic:** read literally, each of the 21 bars keeps its own
band's hue (bar for score 5 is amber, bar for score 16 is green, etc.); all bars render
desaturated except the one matching `submission.innovation_score`, which renders at full
colour. This can be done statically in the SVG generator (compute a desaturated hex/HSL
variant per band colour) — no client-side JS/CSS needed, consistent with the no-JS
inline-SVG pattern already in use.

**Accessibility precedent to carry over:** `_result_innovation.html`'s existing docstring
is explicit that band identity must never be colour-alone (name text always shown
alongside the colour swatch). The new viz should keep a visible score/band label, not
rely on the bar colours alone.

## Notes
Open questions for whoever picks this up (`/ship #0011`):
- Should the new visual replace the current simple colour-swatch+name line in
  `_result_innovation.html`, or sit alongside/above it in the same card?
- Should the curve bulge to the classic Rogers proportions (16/34/34/13.5/2.5%, per
  `INNOVATION-SCORING-TEMPLATE.md`) to visually match `docs/Diffusion_of_ideas.svg`, or
  is a flat/uniform bar strip (simpler to build) acceptable?
- Confirm this should appear on the PDF too (it will, by default, since it's added to the
  shared `_result_innovation.html` partial) — flag if PDF should be skipped instead.

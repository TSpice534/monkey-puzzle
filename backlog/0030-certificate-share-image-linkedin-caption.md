---
id: 0030
title: Certificate-style share image + personalized LinkedIn caption
type: feature
status: shipped
created: 2026-08-30
branch: feature/certificate-share-image-linkedin-caption
---

## Request
Tom (relaying Andrew's review): build a certificate-style image render of a respondent's
result for posting to LinkedIn, plus default caption text. Andrew drafted "Discover your own
sustainability profile, do the scan via this link…"; Tom refined the call-to-action to
"Click this link to take the survey and discover your own sustainability profile!"

Open question — "is it possible to present the image instead of link, so it's directly
visible on LinkedIn" — investigated and resolved with Tom: LinkedIn's link-share dialog only
ever shows a small og:image preview thumbnail; a true native-looking image post needs
LinkedIn's OAuth upload API, which doesn't fit this anonymous, login-free tool. Confirmed
approach instead: a **downloadable certificate image + a copyable caption**, which the user
pastes into LinkedIn themselves as a native image post. Caption is **personalized** — includes
the respondent's actual persona name, not one fixed string for everyone.

## Investigation
Extends the existing share-image pipeline, doesn't replace it:
- app/survey/charts.py::render_share_card_svg(persona) — current 1200x630 SVG (green accent
  bar, eyebrow text, persona name 84px + tagline 34px, flat background, no chart since #0025).
  Certificate design should build on this function/pattern; exact visual treatment (border/
  frame, persona colour, whether to bring back the persona icon) left to build time.
- Rasterization: cairosvg.svg2png(...) via app/asset_cache.py::get_or_render
  (content-addressed cache) — reuse this exact pipeline, don't introduce a new render
  approach (e.g. no headless-browser/Pillow dependency).
- Known pre-existing constraint (not new): #0022's on-disk cache means cache-miss renders
  still run synchronously on Gunicorn sync workers (prod: --workers 3). A more complex
  certificate SVG raises per-render cost on cache misses — flag if render latency becomes
  noticeable, don't silently absorb into this item's scope.
- UI: app/templates/survey/result.html:32-58 ("Share or save your result" card) — add a
  "Download certificate" button (parallel to the existing "Download PDF" button/route
  pattern) and a caption text block + "Copy" button (first clipboard-copy JS in the
  codebase — keep vanilla, no new JS dependency).
- No existing tests cover this area — additive feature, will need new tests for the new
  route/render function, nothing existing to update.

## Notes
- Exact certificate visual design (border/seal/frame treatment, whether persona colour or
  icon appears) intentionally left open for build time — same pattern as #0013's "exact
  visual size/shape... left to build time."
- Exact caption template string (how persona name/tagline/CTA/URL combine into one sentence)
  left to build time, following the CTA sentence Tom confirmed as the base: "Click this link
  to take the survey and discover your own sustainability profile!"
- Out of scope for this item: LinkedIn OAuth/API integration, auto-posting on the user's
  behalf. If Tom wants that later, it's a separate, much larger item (needs a LinkedIn
  Developer app + user auth flow this tool doesn't have).

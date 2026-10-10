---
id: 0059
title: Result page caption textarea cuts off the LinkedIn caption
type: change
status: todo
created: 2026-10-10
branch:
---

## Request
The share caption textarea on the result page has `rows="3"`, so the caption is cut off ("...discover your own") until the user scrolls inside it. Make the whole caption visible without scrolling at phone and desktop widths.

## Investigation
`app/templates/survey/result.html`, `id="share-caption"`. The caption text comes from the top-level `share_caption` key in `content/survey.yaml` (#0030) plus the site URL, so its length can change when Rob and Andrew retune it. Prefer a rows value or auto-sizing in CSS over a hardcoded count; no inline scripts (CSP).

## Notes
Raised by the #0050 reviewer (follow-up). Pre-existing, not caused by #0050. Route: `/quick-ship`.

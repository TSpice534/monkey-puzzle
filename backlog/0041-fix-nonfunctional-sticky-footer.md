---
id: 0041
title: Footer's mt-auto doesn't do anything (no flex parent on body)
type: bug
status: shipped
created: 2026-09-23
branch: quickship/fix-nonfunctional-sticky-footer
---

## Request

`base.html:49`'s `<footer class="footer mt-auto ...">` uses Bootstrap's sticky-footer utility
class, but that only works inside a flex-column parent — `<body>` (`base.html:17`) has no
`d-flex flex-column`/`min-vh-100`. On any page shorter than the viewport (the home page, every
survey step), the footer just sits directly under the content in normal document flow instead of
pinning to the bottom of the viewport, leaving dead whitespace below it — visible on every
screenshot taken during a recent design review.

Fix: either add the flex wrapper (`d-flex flex-column min-vh-100` on `<body>`, `flex-grow-1` on
`<main>`) so the sticky-footer pattern actually works as apparently intended, or drop the unused
`mt-auto` class if a pinned-to-bottom footer isn't actually wanted.

## Investigation

Sourced from an `apple-design` skill design review (screenshots showed the same dead space on
every short page; confirmed by reading `base.html` directly rather than guessing at a CSS cause).

Files touched: `app/templates/base.html` only (lines 17, 44, 49) — no CSS or Python changes
expected if going the `d-flex`/`min-vh-100` route; theme.css needed only if a different fix
direction is chosen.

## Notes

Low-stakes visual polish, not an accessibility issue — purely a "does the CSS do what it looks
like it's meant to do" fix. Good `/quick-ship` candidate rather than a full `/ship`.

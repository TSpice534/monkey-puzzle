---
id: 0058
title: Guard the result PDF at one page with a test, and colour the PDF icon
type: change
status: todo
created: 2026-10-10
branch:
---

## Request
Add a WeasyPrint test that asserts the result PDF renders on exactly one page for the longest real persona description plus a typical "why" answer, so the #0049 fix cannot regress silently. Separately, the persona icon in the PDF renders black instead of the brand green; make it green if WeasyPrint can do it with a fixed hex (no CSS variables in the PDF template).

## Investigation
`app/templates/pdf/result.html`, `app/pdf_utils.py`; existing PDF test only checks the output starts with `%PDF`. The #0049 fix was `.card { display: block; }` in the PDF template, since WeasyPrint sized the flex-column innovation card too tall. Very long free-text "why" answers are unbounded and can still push the PDF to 2 pages; decide whether to cap or accept.

## Notes
Raised by the #0049 reviewer (follow-up) and design review (Low). Route: `/quick-ship`.

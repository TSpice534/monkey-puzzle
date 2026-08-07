---
id: 0025
title: Remove radar chart from PDF, email, and share card (finish #0020)
type: change
status: shipped
created: 2026-08-07
branch: feature/remove-radial-graph-everywhere
---

## Request
Remove the radial/fingerprint chart from the PDF download, the emailed PDF copy, and the
share-card PNG. #0020 removed it from the web result page only (its investigation scoped
narrowly to "the results page" and explicitly left the other three surfaces). Tom confirmed
the intent was to remove it everywhere — this closes that gap.

## Notes
Deletes the now-dead `render_fingerprint_svg` generator and relays out the share card to
fill the freed space. Follow-up correction to #0020, not a new idea.

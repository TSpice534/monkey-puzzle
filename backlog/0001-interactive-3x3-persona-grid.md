---
id: 0001
title: Interactive 3x3 grid replaces weighted-scoring persona classifier
type: feature
status: wontfix
created: 2026-07-15
branch:
---

## Merged into #0003

This item's full content (confirmed persona mapping, axis correspondence, flow
position, grid visual states, investigation) has been merged into
[0003-real-survey-template-and-output-routing.md](0003-real-survey-template-and-output-routing.md),
since building the grid mechanism separately from the real 11-question survey content
turned out to have real technical overlap (shared `Matrix` schema type, and "grid is
step 8 of 11" only makes sense once the other 10 real questions exist). Shipping them as
one item avoids two separate `/ship` passes over the same files.

Marked `wontfix` as a standalone item — not declined as an idea, just consolidated.
Ship via `/ship #0003`, not this item.

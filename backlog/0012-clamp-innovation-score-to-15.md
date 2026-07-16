---
id: 0012
title: Clamp innovation-curve score to 15, shrink the curve graphic to match
type: change
status: shipped
created: 2026-07-17
branch: feature/clamp-innovation-score-to-15
---

## Request
Scores need to be clamped to 15 max. We allow for over-scoring due to the persona
modifier offset, but the final score shown/stored should be clamped to 15 for the
Innovators band — see `docs/INNOVATION-SCORING-TEMPLATE.md`. Reduce the innovation-curve
graphic on the results page to fit the new 0-15 scale.

## Investigation

**Confirmed by reading the template + code:**

`docs/INNOVATION-SCORING-TEMPLATE.md`'s boundary table gives Laggards 0-2, Late Majority
3-7, Early Majority 8-12, Early Adopters 13-14, Innovators **15** (a single point, not a
range). This matches `content/survey.yaml`'s bands for every band *except* Innovators,
whose `max` is currently `20` (`content/survey.yaml:430`) instead of `15`.

Max raw total is 15 (5+5+5 across `motivation`/`ambition`/`space_to_progress`,
`content/survey.yaml:232-260`), and persona modifiers run 0 (`accountant`) to +4
(`activist`, `developer`) (`content/survey.yaml:371-379`) — so an uncapped total can hit
19. That's the "over-scoring due to the offset" in the request: the modifier is allowed
to push the raw sum past 15, but the number that gets banded/displayed should cap there.

`app/survey/persona.py::resolve_innovation_curve` (lines 110-142) sums the 3 questions,
adds the modifier, and returns the raw uncapped `total` as `InnovationCurveResult.score`
— no clamp exists today. Band-matching already has a graceful fallback for out-of-range
totals (`bands[-1]` if `total` exceeds every band's `max`), but the numeric `score` itself
is never capped, so today's "19 of 20" text is possible and, after the yaml fix below,
would become the nonsensical "19 of 15."

**Single source of truth for the stored score:** `submission.innovation_score = ic.score`
at `app/survey/routes.py:175` is the *only* place the resolved score gets persisted, and
`routes.py:93`/`routes.py:97` are the only two places it's read back out (web/PDF/email
context, and the SVG generator call). Clamping inside `resolve_innovation_curve` before
it's returned is therefore sufficient to fix storage, the web result page, the PDF, and
the email bodies in one place — nothing downstream needs a separate clamp.

**The curve graphic needs no code change.** `app/survey/charts.py::render_innovation_curve_svg`
(backlog #0011) already derives its bar count and the "of {hi}" aria-label text
dynamically from the bands config (`lo = min(b['min'] for b in bands)`,
`hi = max(b['max'] for b in bands)` — `charts.py:197-198`, `charts.py:267-269`), not from
a hardcoded 21/20. Once `content/survey.yaml`'s Innovators `max` changes from 20 to 15,
the chart automatically renders 16 bars (0-15) instead of 21, and the aria-label reads
"of 15" — this *is* the "reduce the graphic to fit the new scale" ask, for free.

**Recommended approach (for the coder to confirm, not a hard requirement):** clamp to
`max(b['max'] for b in ic['bands'])` (i.e. derive the ceiling from the bands config, the
same pattern `charts.py` already uses) rather than hardcoding `15` in `persona.py` — keeps
the cap config-driven so a future retune of the template doesn't need a second code
change alongside the yaml edit.

**Files likely touched:**
- `content/survey.yaml` — `innovation_curve.bands`, Innovators entry: `max: 20` → `max: 15`.
- `app/survey/persona.py::resolve_innovation_curve` — clamp `total` before returning it as
  `InnovationCurveResult.score` (band-matching logic can stay as-is; it already resolves
  to Innovators for any total ≥ 15 via the existing fallback).
- No changes expected in `charts.py`, `routes.py`, or any template.

**Test surface (scope awareness, not read in detail):** `tests/test_persona.py`,
`tests/test_loader.py`, `tests/test_real_survey_e2e.py`,
`tests/test_innovation_curve_verification.py`,
`tests/test_innovation_curve_visualisation_verification.py`, and `tests/test_sharing.py`
all reference innovation-curve scoring/bands and likely have fixtures or assertions
hardcoded to the old 0-20 / 21-bar scale (e.g. `_CURVE_BANDS` fixtures with `max: 20`,
"999 of 20"-style aria-label checks). These should be reviewed for the old ceiling during
implementation.

## Notes
`docs/INNOVATION-SCORING-TEMPLATE.md` has an uncommitted local edit (Innovators boundary
"15-20" → "15") already sitting in the working tree — that edit is the source of this
request, not something this backlog item's commit touches; it should be committed
separately (or as part of the eventual `/ship #0012` implementation commit).

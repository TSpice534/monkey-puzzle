---
id: 0038
title: Rebalance innovation-curve band cutoffs to match documented target shares
type: change
status: shipped
created: 2026-09-23
branch: feature/rebalance-innovation-curve-band-cutoffs
---

## Request

Band cutoffs in `content/survey.yaml` (~396-447) don't match the documented target split in
`docs/INNOVATION-SCORING-TEMPLATE.md` (16/34/34/13.5/2.5% across Laggards/Late Majority/Early
Majority/Early Adopters/Innovators). Modeling every possible answer combination (5×5×5 question
options × 9 personas = 1,125 combos) against the current bands gives roughly 0/15/60/16/9% —
Early Majority absorbs nearly double its intended share; Innovators (a single-point band at
exactly 15, patched by a silent overflow rule folding every total ≥15 into it) comes out more
common than intended.

Fix: rebalance the Late Majority / Early Majority / Early Adopters / Innovators cutoffs toward
the documented shares, rescaled across just those four reachable bands (34/34/13.5/2.5, since
Laggards' 16% never manifests). **Explicit constraint: Laggards stays permanently unreachable**
(0-2, below the true floor of 3) — do not widen it into range the way a naive proportional
rebalance would. Exact new cutoff values are a starting point for whoever picks this up to
compute/confirm at `/ship` time, not fixed here.

## Investigation

Modeled distribution above assumes every question-option/persona combination is equally likely
— it's a model of the scoring logic's shape, not real respondent data (no usable local or live
submission data exists for this scoring version). Whoever ships this should re-run the same
enumeration against `content/survey.yaml`'s bands *after* #0036 and #0037 have landed, since
both change the score distribution this rebalance needs to target.

Files touched: `content/survey.yaml` — `innovation_curve.bands` (Late Majority / Early Majority
/ Early Adopters / Innovators `min`/`max` only; Laggards left untouched at `0-2`).

## Notes

Depends on #0036 (motivation-direction fix) and #0037 (ambition/space_to_progress monotonic
fix) landing first — both change the score distribution this rebalance is modeled against, so
#0038 should be scoped/shipped last of the three.

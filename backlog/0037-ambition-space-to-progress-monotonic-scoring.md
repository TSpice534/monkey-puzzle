---
id: 0037
title: Make ambition/space_to_progress scoring monotonic to match Innovators tagline
type: change
status: in-progress
created: 2026-09-23
branch: feature/ambition-space-to-progress-monotonic-scoring
---

## Request

The Innovators band's tagline/description (`content/survey.yaml` ~449-454) says Innovators are
risk-tolerant, willing to adopt technologies that may fail — but `ambition` and
`space_to_progress` are deliberately U-shaped per #0002 (the practical middle option scores
highest, both extremes score lowest). So the only way to mathematically reach Innovators was the
practical/balanced middle answer on both, not the bleeding-edge extreme — a direct contradiction
between what the band claims to reward and what the scoring actually rewarded.

Tom decided (2026-09-23): fix by making both questions monotonic, same direction as the #0036
motivation fix, rather than rewriting the tagline. This reverses a decision explicitly confirmed
with Rob/Andrew in #0002 — noted for awareness, not as a reason to hold the fix.

## Investigation

- `ambition` (`content/survey.yaml:246-255`) is already listed in ambition-descending order —
  "sector leading" (most extreme/ambitious) → "progressive and innovative" → "adopt latest
  innovative practice" (current U-shape peak, middle) → "keeping pace" → "get my work
  done"/legal-obligations-only (least ambitious). Flipping current scores `1,3,5,3,1` to
  `5,4,3,2,1` (score by list position, most-ambitious end highest) makes it monotonic without
  reordering options.
- `space_to_progress` (`content/survey.yaml:257-268`) is structurally different — a genuine
  two-ended spectrum centred on "Balanced between commitments and capacity" (position 3), not a
  linear ambition scale like `ambition`. There's no obvious a-priori direction ("lots of
  capacity" vs. "fully committed" isn't inherently more or less "innovator"). Recommended
  default for whoever ships this: capacity-to-experiment end scores highest — "Few commitments,
  lots of capacity" = 5 down to "No capacity, fully committed" = 1 (`5,4,3,2,1` by list
  position, same pattern as `ambition`) — reasoning: spare capacity is what enables risk-taking
  and experimentation, consistent with the tagline. Flag this specific direction for Tom to
  confirm at `/ship` time — it's a genuine judgment call, distinct from `ambition`'s unambiguous
  ordering.

## Notes

Independent of #0036; not blocked. Should land before #0038 (band rebalance), since it also
shifts the score distribution #0038 is modeled against — ship order: #0036, #0037, #0038.

---
id: 0036
title: Fix motivation question scoring direction (currently backwards)
type: bug
status: todo
created: 2026-09-23
branch:
---

## Request

The `motivation` question in `content/survey.yaml` (lines 240-244) scores backwards for a
Rogers innovation-curve — "I feel the need to act on this topic" scores 1 (lowest) and "I do
only what is asked/required" scores 5 (highest), the opposite of what should feed an
Innovators-leaning result. This is the likely cause of Andrew's report that he keeps landing on
Early Adopters despite picking what he believes are the most proactive answers.

Fix: flip the five scores (`score: 6 - score` for each option), consistent with the direction
persona modifiers already use (Activist/Inventor carry the highest modifier, +4).

## Investigation

`git log -p` on `content/survey.yaml` shows this direction has been unchanged since the original
#0002 implementation (commit `7f8e052`) — it matches what was confirmed with Rob/Andrew at the
time. Only the label text on the score-5 option was reworded later, from "It is part of my role"
to "I do only what is asked/required". Noting this for whoever picks it up, not as a reason to
hold the fix — Tom has confirmed he wants it fixed regardless, since it's scoring the wrong way
in practice today.

Single file touched: `content/survey.yaml:240-244`.

## Notes

Should land before #0038 (band rebalance) — that item's cutoffs are modeled against the score
distribution this fix changes.

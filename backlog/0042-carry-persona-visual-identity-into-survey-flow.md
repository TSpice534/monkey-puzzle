---
id: 0042
title: Carry some of the result page's visual identity into the survey flow
type: change
status: todo
created: 2026-09-23
branch:
---

## Request

The result page has real visual personality (the 9 hand-styled persona icons, the colour-coded
relationship grid, the innovation-curve bell chart, the certificate download), but the home page
and all 11 survey steps are plain, generic Bootstrap: white card, one green accent, system sans
serif, no imagery. For a tool designed to be taken once and shared/re-taken virally, all of the
personality is currently banked for the very end — nothing earlier builds anticipation or
reinforces "this is The Monkey Puzzle" while someone's actually answering questions.

Suggestion (not a fixed spec — needs a design pass, not just an implementation): work some of the
persona icon set or the brand green more visibly into the survey-taking steps themselves, e.g. a
subtle icon treatment on the progress bar, or icon hints tied to which persona each answer leans
toward. Should stay tasteful and not spoil/hint at the result before the end.

## Investigation

Sourced from an `apple-design` skill design review's craft lens ("is it a template? does it have
a point of view throughout, not just at the end?") — not a fresh code investigation, since this
is a design-direction suggestion rather than a located bug. No specific files identified as the
right touch point; that's part of what a design pass on this item needs to decide.

## Notes

Lowest priority of the four items filed from this review — genuine craft/polish suggestion, not
a defect. Explicitly flagged in the review as "a defensible choice either way" (front-loading
personality onto the payoff is a reasonable structure on its own) — worth Tom/Rob/Andrew's call
on whether it's worth spending design time on, not an obvious must-fix.

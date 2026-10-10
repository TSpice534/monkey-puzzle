---
id: 0057
title: Review Laggards tagline and exclamation-mark tone
type: change
status: todo
created: 2026-10-10
branch:
---

## Request
The Laggards band tagline reads 'You are a Laggard. Wanker.' and it appears on the result page, certificate and share caption. Separately, the intro and persona taglines use exclamation marks. Review both against the 'know yourself, not what you're doing wrong' framing.

## Investigation
Content lives in `content/survey.yaml` (`innovation_curve.bands[0].tagline`, persona taglines, intro copy in `index.html`). Rob and Andrew own and retune this without a deploy. Note the tagline is currently unreachable (Laggards 0-2 is unreachable by design, see #0038), so it may never show; confirm.

## Notes
Owner: Rob and Andrew. This is a content question, not a design task. Do not edit survey.yaml copy without their agreement.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

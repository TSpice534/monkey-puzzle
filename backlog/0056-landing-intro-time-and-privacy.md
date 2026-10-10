---
id: 0056
title: Landing page intro: say how long it takes and what happens to answers
type: feature
status: todo
created: 2026-10-10
branch:
---

## Request
The intro does not say the survey is 11 questions or how long it takes, or what happens to the answers. Add both.

## Investigation
Intro paragraph is in `app/templates/index.html` (`.landing-intro`, max 40rem). Suggested wording for review: '11 questions, about 3 minutes' and a one-line privacy note linking to the privacy page. Content and tone are Rob and Andrew's, so wording needs their sign-off. Depends on the privacy-link item.

## Notes
Owner: Rob and Andrew (copy). Route: `/request` content ask first, then `/quick-ship` once wording is agreed. Do not write the final copy unprompted.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

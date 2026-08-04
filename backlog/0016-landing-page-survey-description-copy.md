---
id: 0016
title: Add survey description copy to landing page
type: change
status: todo
created: 2026-08-04
branch:
---

## Request

Add the following copy to the landing page:

"This short survey is designed to help you capture a snapshot of your current situation,
helping you to understand how you or your organisation are currently approaching
sustainability. On completion you will receive personalised results that you can share!"

## Investigation

- The landing page is `app/templates/index.html`, served by the `main` blueprint
  (`app/main/routes.py`). It's a single small template: extends `base.html`, an `<h1>`,
  one `<p class="lead">` placeholder blurb, and a "Begin" button linking to
  `url_for('survey.start')`.
- Copy-only change to that `<p class="lead">` — no backend, model, or route changes, no
  edge cases (static text).

## Notes

- Open question for whoever ships it: replace the existing `<p class="lead">` blurb with
  this new copy, or keep the existing blurb and add this as a second paragraph beneath
  it. Tom didn't specify.

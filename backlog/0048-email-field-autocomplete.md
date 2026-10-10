---
id: 0048
title: Email field: add autocomplete and ellipsis placeholder
type: change
status: shipped
created: 2026-10-10
branch: quickship/email-field-autocomplete
---

## Request
Add `autocomplete="email"` and `inputmode` to the result-page email field and end the placeholder with an ellipsis.

## Investigation
`app/templates/survey/result.html` line ~65 (`type="email"`, placeholder `you@example.com`). Web Interface Guidelines forms rules.

## Notes
Route: `/quick-ship`. Tiny. Batch with the privacy and favicon item if convenient.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

Shipped without the placeholder ellipsis: the convention applies to prompts such as "Search…", not example values.

---
id: 0026
title: Rename "Where you sit on the innovation curve" heading
type: change
status: shipped
created: 2026-08-30
branch: quickship/innovation-curve-heading-focus-group
---

## Request
On the Your Sustainability Who result page, change the heading "Where you sit on the
innovation curve" to "Your focus group on the innovation curve".

## Investigation
Exact string "Where you sit on the innovation curve" appears in 5 places:
- app/templates/survey/_result_innovation.html:13 — the result-page heading (this request's target); shared partial, also feeds the PDF.
- app/templates/email/result.html:18 and app/templates/email/result.txt:12 — same wording in the result email (HTML + plain text).
- tests/test_real_survey_e2e.py:860,864 and tests/test_innovation_curve_verification.py:115,119 — hard-assert the current string, will need updating alongside the copy change.

## Notes
Request named only the result page. Open question for whoever picks this up (or for
Tom to confirm before /ship): should the email templates (HTML + plain text) get the
same wording change for consistency, or stay as "Where you sit..."? Recommend matching
them — same card, same copy — but confirm before implementing since it wasn't explicitly asked.

---
id: 0021
title: Cap free-text answer length and rate-limit /start and /step
type: bug
status: shipped
created: 2026-08-04
branch: feature/cap-freetext-length-ratelimit
---

## Request
Close a storage-exhaustion DoS: `/start` and `/<token>/step` are unauthenticated and unlimited, and `short_text` answers have no length cap, so an attacker can script unlimited `Submission` rows and stuff multi-megabyte strings into the `answers` JSON column.

## Investigation
From the codebase-audit security lens (2026-08-04):
- `app/survey/routes.py:48` — `_read_answer` for `short_text` only `.strip()`s the value, no length cap.
- `app/survey/routes.py:203` — `/start` route has no rate limit.
- `app/__init__.py:15` — Flask-Limiter `default_limits=[]`, so only `/<token>/email` (explicitly decorated) is throttled.
- `_question_short_text.html` textarea has no `maxlength` client-side either.

## Notes
Suggested fix direction (from the auditor, not yet scoped): cap free-text length server-side in `_read_answer` (e.g. reject/truncate over 2-4 KB), add `maxlength` to the textarea, and apply a modest global or `/start`-specific rate limit default.

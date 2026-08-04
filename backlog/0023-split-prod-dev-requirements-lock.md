---
id: 0023
title: Split pytest and other test-only deps out of the production requirements lock
type: change
status: todo
created: 2026-08-04
branch:
---

## Request
`pytest` and its transitive deps end up installed on the production server because the compiled `requirements.txt` isn't split from the dev/test lock — enlarges prod attack surface and dependency footprint for no runtime benefit.

## Investigation
From the codebase-audit dependencies lens (2026-08-04):
- `requirements.in` labels `pytest` `# Test-only`, but the compiled `requirements.txt:28,34,39` folds it (plus `iniconfig==2.3.0`, `pluggy==1.6.0`) into a single flat lock.
- `DEPLOY.md:101` runs `pip install -r requirements.txt` on the production server, installing the test framework on live hosts.

## Notes
Suggested fix direction (from the auditor, not yet scoped): maintain a separate `requirements-dev.in`/`requirements-dev.txt` via pip-tools layered locks, and have `DEPLOY.md` install only the prod lock on the server.

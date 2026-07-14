# Changelog

All notable changes are documented here. Add a bullet to `Unreleased` after every completed task on `dev`. On release, rename this section to `[v<version>] — YYYY-MM-DD` and add a fresh `Unreleased` block at the top.

---

## Unreleased

- Docs: added `CLAUDE.md`, `CONTEXT.md`, and `backlog/CONTEXT.md` (gitignored, local-only), plus `CHANGELOG.md` and `VERSION` (tracked), replicating the Donut Toolkit's project-navigation doc system for this repo
- Feature: Phase 1 skeleton — Flask app factory with CSP nonce + full security-header set (ported from Donut Toolkit, stripped of auth/admin/mail/limiter/client-config), `main`/`errors` blueprints, base templates, anonymous `Submission` model (token, answers JSON, persona_id, score_vector, timestamps) + first Alembic migration. Pytest suite (24 tests) covering security headers, error pages, model persistence, and the prod dev-secret boot guard

---

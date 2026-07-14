# Changelog

All notable changes are documented here. Add a bullet to `Unreleased` after every completed task on `dev`. On release, rename this section to `[v<version>] — YYYY-MM-DD` and add a fresh `Unreleased` block at the top.

---

## Unreleased

- Docs: added `CLAUDE.md`, `CONTEXT.md`, and `backlog/CONTEXT.md` (gitignored, local-only), plus `CHANGELOG.md` and `VERSION` (tracked), replicating the Donut Toolkit's project-navigation doc system for this repo
- Feature: Phase 1 skeleton — Flask app factory with CSP nonce + full security-header set (ported from Donut Toolkit, stripped of auth/admin/mail/limiter/client-config), `main`/`errors` blueprints, base templates, anonymous `Submission` model (token, answers JSON, persona_id, score_vector, timestamps) + first Alembic migration. Pytest suite (24 tests) covering security headers, error pages, model persistence, and the prod dev-secret boot guard
- Feature: Phase 2 data engine — `content/survey.yaml` loader + schema validation (`app/survey/loader.py`), a realistic placeholder `survey.yaml` (13 questions across Rob's seven axes, all nine personas with stub allies/case-studies/resources), and `SURVEY_PATH` config
- Feature: Phase 3 survey flow — data-driven `survey.start`/`survey.step`/`survey.result` routes persisting answers to `Submission.answers` by question id (zero-based option indices); single/multi/spectrum/short_text widgets built from native HTML + CSS (`:checked` sibling styling) instead of Alpine.js, with one small nonce'd vanilla script for the spectrum slider's live label — resolves the Phase 1 Alpine/CSP conflict without weakening the CSP
- Feature: Phase 4 persona classifier + result page — `app/survey/persona.py` (score/apply_modifiers/classify, deterministic tie-break) and `app/survey/charts.py` (`render_fingerprint_svg`, an inline-SVG radar over the nine personas' `score_vector`), plus the result page (persona card + radar chart)
- Tests: `tests/test_loader.py`, `tests/test_persona.py`, `tests/test_survey_routes.py` (60 new tests, 84 total) covering schema validation, the data-driven weight-swap contract, deterministic persona classification for all nine personas, and the full survey flow including edge cases (unknown token, out-of-range step, result-before-completion, security headers)

---

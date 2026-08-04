---
id: 0018
title: Rename Developer→Inventor and Advocate→Architect personas (id + copy)
type: change
status: todo
created: 2026-08-04
branch:
---

## Request

Tom rewrote `docs/PROFILES-TEMPLATE.md` (uncommitted local edit) and wants the changes
implemented into the survey.

## Investigation

Diffed the new (uncommitted) template against the last committed version
(`git diff HEAD -- docs/PROFILES-TEMPLATE.md`, last committed at `06a33d2`, backlog
#0004). The diff is small and clean — two persona renames, everything else (focus/
description/tagline/relationships copy) unchanged:

- **"Developer" → "Inventor"** (persona described as "develop new solutions")
- **"Advocate" → "Architect"** (persona described as "create space to work on topic")

Confirmed with Tom this is a **full internal persona-id rename**
(`developer`→`inventor`, `advocate`→`architect`), not just the displayed `name:`/
tagline copy. Grepped `content/survey.yaml` and `app/survey/icons.py` to map every
reference that needs updating:

- Persona map keys (`developer:`, `advocate:` blocks)
- `icon:` paths (`icons/developer.svg`, `icons/advocate.svg`) — the actual SVG files
  under `app/static/icons/` (added in backlog #0005) need renaming too, resolved by
  persona id via `app/survey/icons.py::persona_icon`
- Cross-persona relationship lists — `natural_allies`/`friends`/`necessity` on *other*
  personas reference `developer`/`advocate` by id (accountant's `friends`, developer's
  own `natural_allies`, advocate's own `natural_allies`, communicator's
  `natural_allies`, cooperator's `necessity`, entrepreneur's `friends`) — every inbound
  reference needs updating alongside the two personas' own blocks
- `profile_grid.cells` — two of the 9 grid cells map directly to `persona: developer` /
  `persona: advocate`
- `scoring.tie_break` list and `innovation_curve.persona_modifiers` keys
- `case_studies`/`resources` placeholder URLs embed the old name (e.g.
  `case-studies/developer`, `resources/developer-prototyping`) — cosmetic, but worth
  renaming for consistency while touching the file anyway
- ~7 test files reference these ids by name: `test_persona.py`, `test_loader.py`,
  `test_survey_routes.py`, `test_sharing.py`, `test_persona_copy_verification.py`,
  `test_audience_routing.py`, `test_real_survey_e2e.py`, plus fixtures
  `survey_grid.yaml`/`survey_min.yaml`/`survey_audience.yaml`

Source: docs-only for the rename intent, plus two targeted greps (`survey.yaml`,
`icons.py`) to scope the blast radius.

## Notes

- **Depends on / overlaps backlog #0017** (profile question redesign — grid replaced by
  two button rows, not yet built): both touch `profile_grid.cells`'
  `developer`/`advocate` entries. Whichever ships first should leave the other a clean
  merge — check for conflicts before landing both.
- Test fixtures (`survey_grid.yaml`, `survey_min.yaml`, `survey_audience.yaml`) may use
  `developer`/`advocate` as arbitrary placeholder ids unrelated to real persona copy —
  check each file individually rather than a blind repo-wide find/replace.
- Don't forget the actual SVG files in `app/static/icons/` need renaming alongside the
  `icon:` path references.

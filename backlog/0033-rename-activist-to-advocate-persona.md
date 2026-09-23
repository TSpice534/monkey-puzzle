---
id: 0033
title: Rename Activist persona to Advocate (id + copy)
type: change
status: in-progress
created: 2026-09-23
branch: feature/rename-activist-to-advocate-persona
---

## Request

Change "Activist" to "Advocate" across the whole app. Update description to:
"You compel people to have the conversations we need and make sure the message is heard"

## Investigation

Source: `content/survey.yaml` (owned by Rob/Andrew per `CLAUDE.md`) plus backlog
`0018-rename-developer-and-advocate-personas.md`, the direct precedent for this exact kind
of change (persona rename: Developer→Inventor, Advocate→Architect, confirmed with Tom then
as a **full internal persona-id rename**, not just display copy). Tom confirmed this
request should follow the same precedent: full id rename `activist` → `advocate`, not
display-only.

Grepped `content/survey.yaml` for every `activist` reference to map the blast radius:

- **Persona block itself** (`content/survey.yaml:139-159`): key `activist:` → `advocate:`,
  `name: "The Activist"` → `"The Advocate"`, `icon: "icons/activist.svg"` →
  `"icons/advocate.svg"`, `description` copy → Tom's new text ("You compel people to have
  the conversations we need and make sure the message is heard..." — keep the rest of the
  paragraph, which is unchanged: "...Your focus is creating as much push as possible for
  the cause at heart — standing firm on your ground and speaking in clear, strong
  language."), and `description_organisation` should get the matching organisation-voice
  edit following the existing pattern (individual "You force..." / org "Your organisation
  forces..." pairing) — i.e. "Your organisation compels people to have the conversations
  we need and makes sure the message is heard...". `case_studies`/`resources` placeholder
  URLs (`case-studies/activist`, `resources/activist-campaigns`) — cosmetic, rename for
  consistency while touching the file, matching #0018's approach.
- **Icon file**: `app/static/icons/activist.svg` needs renaming to `advocate.svg`
  alongside the `icon:` path update (confirmed the file exists; resolved by persona id via
  `app/survey/icons.py::persona_icon`, per #0018).
- **Inbound relationship reference**: `implementer`'s `necessity: [activist]`
  (`content/survey.yaml:70`) is the only other persona referencing `activist` by id —
  needs updating to `[advocate]`.
- **`scoring.tie_break` list** (`content/survey.yaml:372`) and
  **`innovation_curve.persona_modifiers`** (`content/survey.yaml:389`, value `4`) — both
  keyed by persona id, need the `activist` key renamed to `advocate`.
- **`profile_grid.cells`** (`content/survey.yaml:504`) — one cell maps directly to
  `persona: activist`, needs `persona: advocate`.
- **Docs**: `docs/PRODUCTION-PLAN.md:78` has an `activist` reference in a commented
  example (not live content, but worth checking alongside the yaml edit for consistency).
- **Tests** (~9 references across `test_loader.py`, `test_role_phrase_macro.py`,
  `test_persona.py`, `test_survey_routes.py`, `test_grid_flow.py`,
  `test_grid_relationship_colouring.py`, `test_real_survey_e2e.py`) plus fixtures
  (`survey_grid.yaml`, `survey_min.yaml`, `survey_audience.yaml`) reference `activist` by
  id — per #0018's note, check each file individually rather than a blind repo-wide
  find/replace, since fixtures may use `activist` as an arbitrary placeholder id unrelated
  to the real persona copy.

## Notes

- Direct precedent: #0018 (shipped) did the equivalent rename for two other personas —
  follow the same checklist (id, icon file + path, inbound relationship refs, tie_break,
  innovation_curve modifiers, profile_grid cell, tests/fixtures individually, docs).
- Tom's new description text only covered the individual-voice `description:` field;
  `description_organisation` needs the matching organisation-voice edit — flagged above,
  worth a quick confirmation from Tom/Rob/Andrew during `/ship` rather than guessing wording
  beyond the direct pattern substitution ("You compel" → "Your organisation compels", "make
  sure" → "makes sure").
- No other persona is currently named "Advocate" (the original Advocate was renamed to
  Architect in #0018), so no id collision.

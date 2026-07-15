---
id: 0005
title: Vector icons for persona cards and grid
type: feature
status: todo
created: 2026-07-15
branch:
---

## Request

Add vector icons for each of the 9 personas, shown on persona cards and in the grid —
per the reference screenshot (9 icons: Developer, Advocate, Cooperator, Implementer,
Entrepreneur, Connecter, Documenter, Communicator, Activist, each a simple line-art
mark paired with the persona name).

## Investigation

**Current state:** no icon concept exists anywhere in this project yet.
- `content/survey.yaml` `personas:` entries have no `icon` field; `loader.py::_validate_personas`
  doesn't check for one.
- No icon assets exist in `app/static/` (only `css/theme.css`).
- Bootstrap Icons is already a CDN dependency (per root `CLAUDE.md` tech-stack table) — usable
  as a placeholder icon source without adding a new dependency.
- Persona names have moved on from the screenshot: it shows the pre-#0002/#0004 names
  (`Documenter`, `Connecter`); the live personas are `Accountant`, `Connector`, etc. (9 ids:
  accountant, implementer, developer, advocate, communicator, activist, connector, cooperator,
  entrepreneur — see `content/survey.yaml`). Icon mapping should go by persona **id**, not by
  matching the screenshot's label text.

**Touch points (3 templates + schema, all reused verbatim by PDF per CLAUDE.md):**
- `content/survey.yaml` — add an `icon:` field to each of the 9 `personas:` entries.
- `app/survey/loader.py::_validate_personas` — add `icon` to the required-non-empty-string
  field check (same pattern as existing `tagline`/`description` checks at loader.py:76-78).
- `app/templates/survey/_persona_card.html` — render the icon next to `persona.name` (h1).
  Reused verbatim by `pdf/result.html` (WeasyPrint) per CLAUDE.md's Templates section, so the
  icon shows on the PDF automatically. Not reused by email (email inlines its own persona
  markup, pre-existing gap per CLAUDE.md — out of scope here).
- `app/templates/survey/_result_grid.html` — render each cell's persona icon alongside
  `cell_persona.name` (currently text-only, `_result_grid.html:32`).
- `app/templates/survey/_question_grid.html` — cells are currently blank (no persona name
  shown at question time, by design — see file's header comment) but per Tom's chosen scope
  ("card and grid") they should show the icon too, so respondents get a visual hint of what
  each cell represents before picking. This is a small design deviation from today's
  "blank until answered" grid — flagging it, not blocking on it, since Tom picked "grids too."

**Decisions from Tom:**
1. **Icon source — placeholder now, swap later.** Ship with Bootstrap Icons (or similarly
   simple stock icons) as a stand-in per persona, structured so swapping in final custom SVG
   art later is a small follow-up (just change the `icon:` value/asset path, no template
   rework). Do not attempt to hand-draw a custom icon set matching the screenshot's exact
   line-art style — that requires real design assets Tom doesn't have yet.
2. **Scope — card + both grid views.** Icons appear on the result persona card, the labelled
   result grid, and the blank question-time grid.

## Notes

- Confirm final `icon:` value format when scoping: a Bootstrap Icons class name (e.g.
  `bi-lightbulb`) is simplest and needs no new static assets; an SVG-per-persona under
  `app/static/icons/` is closer to the screenshot's bespoke combined marks but is more work
  and still placeholder art until real assets land.
- `_question_grid.html`'s cells are blank by design today (header comment, line 1-6) — adding
  icons there is a UX change beyond "just theming," worth a quick gut-check with Tom at
  `/ship` time given it changes what's visible before a respondent answers.

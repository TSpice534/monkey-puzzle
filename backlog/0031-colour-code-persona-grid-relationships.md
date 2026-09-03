---
id: 0031
title: Colour-code Natural Allies / Friends / Necessities on result-page persona grid
type: feature
status: shipped
created: 2026-08-30
branch: feature/colour-code-persona-grid-relationships
---

## Request
Colour code and highlight "Natural Allies", "Friends" and "Necessities" on the persona
grid on the results page.

## Investigation
**Data already available** (`content/survey.yaml`, loaded via `app/survey/loader.py`):
each persona carries `natural_allies` / `friends` / `necessity`, each a list of persona
ids (validated + defaulted to `[]` at `app/survey/loader.py:92` and `:536-538`). Confirmed
overlap case exists in real data: persona `inventor` (content/survey.yaml:77-92) lists
`architect` under both `natural_allies` and `necessity` — so a single cell can need two
relationship colours simultaneously for some respondents.

**Render path today** (`app/templates/survey/_result_grid.html`):
- Iterates the 9 `grid_question.cells` (built by `app/survey/routes.py::_profile_grid_context`,
  routes.py:109-149), each resolving to a `cell_persona`.
- Only two states exist: `grid-cell--selected` (the respondent's own cell, exact `[x,y]`
  match) and `grid-cell--muted` (everything else). No relationship awareness at all today.
- `persona` (the classified persona) is already passed to `result.html` at
  routes.py:318-320 — it's the source of the `natural_allies`/`friends`/`necessity` lists
  to check each `cell.persona` against.

**CSS pattern to follow** (`app/static/css/theme.css:93-157`): existing modifier-class
convention — `.grid-cell`, `.grid-cell--result`, `.grid-cell--selected`,
`.grid-cell--muted`. New relationship classes should follow the same
`.grid-cell--<modifier>` naming (e.g. `.grid-cell--ally`, `.grid-cell--friend`,
`.grid-cell--necessity`), picking 3 distinct colours that don't collide with
`--brand-primary` (already used for `--selected`) or the muted grey. The innovation-curve
bands (`content/survey.yaml`'s `innovation_curve.bands`, each with a `colour` hex) are the
only existing precedent for "colour meaning" in this app, but relationship colours aren't
persona/content-driven — they'd be fixed in `theme.css`, not `survey.yaml`, since the
categories (`natural_allies`/`friends`/`necessity`) are fixed schema, not per-survey config.

**Legend**: no existing legend pattern in this app to copy (the innovation-curve chart and
persona-relationship prose, `_persona_card.html`'s "You probably work closely with..."
sentences from backlog #0028, are self-labelled, not colour-keyed). New markup inside
`_result_grid.html`'s card, likely a small colour-swatch + label row, styled inline the
same lightweight way as the rest of the card (Bootstrap 5.3 utility classes, no new
component).

## Notes
Resolved with Tom at filing time:
- **Overlap handling**: when a related persona's cell matches more than one of the current
  persona's relationship categories (e.g. the `inventor`/`architect` case), show a
  **split/stacked colour** on that cell — both relationship colours visible at once (e.g.
  a diagonal split or a small dual-swatch marker) — not a single colour picked by
  precedence.
- **Legend**: yes, add a visible legend/key (colour → Natural Allies / Friends /
  Necessities) below or beside the grid, not colour-only.

Open questions for whoever ships this (`/ship #0031`):
- Exact 3 colours to use — pick from the existing brand palette in `theme.css`'s `:root`
  custom properties, avoiding `--brand-primary`/the muted grey already in use.
- Exact visual treatment for the split/stacked dual-relationship case (diagonal CSS
  gradient split vs. two small corner dots vs. something else) — informed by what stays
  legible at the grid's small mobile size (theme.css:330-334 already shrinks the grid
  under 767px).
- The respondent's own selected cell shouldn't ever also need a relationship colour (a
  persona can't be its own ally/friend/necessity per the data) — worth a defensive check
  rather than assuming it can't happen.

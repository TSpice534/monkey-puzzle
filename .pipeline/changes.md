# Changes — Backlog #0005: Vector icons for persona cards and result grid

Implemented exactly per `.pipeline/spec.md` (no open questions — both decisions were
Tom-confirmed already: SVG-per-persona file, and scope = persona card + labelled result
grid only, not the question-time grid).

## Files created

- **`app/static/icons/<id>.svg`** (9 files: `accountant`, `implementer`, `developer`,
  `advocate`, `communicator`, `activist`, `connector`, `cooperator`, `entrepreneur`) —
  fetched live from the Bootstrap Icons 1.11.3 CDN per the spec's suggested mapping
  (`calculator`, `tools`, `code-slash`, `megaphone`, `chat-dots`, `lightning-charge`,
  `diagram-3`, `people`, `rocket-takeoff`), then stripped to the required contract:
  `viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" focusable="false"`, no
  `width`/`height`/`class`/`style`/`<script>`. Path data is verbatim from the CDN source
  (MIT-licensed).
- **`app/survey/icons.py`** — new `persona_icon(persona)` function, copied verbatim from
  the spec: reads `persona['icon']` (a static-relative path) off disk once, caches the raw
  SVG string keyed by path, returns it as `markupsafe.Markup`. Returns empty `Markup` if
  the persona has no `icon` or the file can't be read (`OSError` swallowed) — never raises.

## Files modified

- **`content/survey.yaml`** — added `icon: "icons/<id>.svg"` to all 9 persona blocks
  (placed right after `tagline`, before `description`), pointing at the 9 new static files.
- **`app/survey/loader.py`** (`_validate_personas`) — added an optional non-empty-string
  check for `icon`, inside the per-persona loop, right after the required-field loop
  (mirrors the existing `label_organisation` check). Not added to the required
  `('name', 'tagline', 'description')` tuple — kept optional per the spec's explicit
  rationale (avoids touching the 3 test fixtures / `_base_config()` builder for zero
  functional gain; real-content completeness is a dedicated test, left for the Tester
  stage per the spec's own "Tests" section).
- **`app/__init__.py`** — imports `persona_icon` and registers it as a Jinja global
  (`app.jinja_env.globals['persona_icon']`) right after the blueprint registrations, so
  both the browser render and the WeasyPrint PDF render (same Jinja env) can call it.
- **`app/templates/survey/_persona_card.html`** — the `<h1>` now renders
  `{% if persona.icon %}<span class="persona-icon persona-icon--card">{{ persona_icon(persona) }}</span> {% endif %}`
  before `persona.name`. No `| safe` (helper already returns `Markup`). This partial is
  shared verbatim by the web result page and `pdf/result.html`.
- **`app/templates/survey/_result_grid.html`** — each result-grid cell now renders
  `{% if cell_persona.icon %}<span class="persona-icon persona-icon--grid">{{ persona_icon(cell_persona) }}</span>{% endif %}`
  above `cell_persona.name`. `_question_grid.html` (question-time grid) was **not**
  touched, per the spec's scope guardrail.
- **`app/templates/pdf/result.html`** — appended `.persona-icon` / `.persona-icon svg` /
  `.persona-icon--card` rules to the existing inline `<style>` block (literal hex
  `#2e7d32` for `--brand-primary`, since this template doesn't load `theme.css`'s custom
  properties). Only card rules — the PDF doesn't include `_result_grid.html`.
- **`app/static/css/theme.css`** — appended a `.persona-icon` / `.persona-icon svg` /
  `.persona-icon--card` (2rem, brand-primary colour) / `.persona-icon--grid` (1.5rem, no
  colour override) block after the existing grid rules. Also added `flex-direction: column;
  gap: 0.25rem;` to `.grid-cell--result` so the icon stacks above the persona name (the
  cell was already `display: flex` centred). Per the spec, left the resulting cosmetic
  quirk alone: in the selected cell, the `::before` checkmark now sits above the icon in
  the column flex — acceptable, not "fixed."

## Docs updated (CLAUDE.md / CONTEXT.md — both gitignored, local-only, not `git add`-ed)

Both docs describe the exact areas this change touches (static assets inventory, the
`app/survey/` module list, `content/survey.yaml`'s persona schema, and the
inline-SVG/PDF-duplicate-CSS template pattern), so both were updated:

- **`CLAUDE.md`** — current-status paragraph now mentions backlog #0005; project-structure
  tree gained `icons.py` under `app/survey/` and `static/icons/<id>.svg` under
  `app/templates/`'s static listing; "Survey content" gained a bullet for the optional
  `icon` field; "Templates" gained a bullet documenting the inline-`<svg>`-not-`<img>`
  decision, the `persona_icon()` global, the guard-on-`persona.icon` pattern, and the
  PDF's duplicated CSS.
- **`CONTEXT.md`** — status intro gained a paragraph on backlog #0005; "What's actually
  built" gained a "Persona icons" bullet; the `content/survey.yaml` section gained a
  mention of the new `icon` field; a new "Decisions taken (backlog #0005 — vector icons
  for persona cards and result grid)" section was added (mirroring the existing #0002/
  #0003/#0004 decision sections) covering: inline-SVG-not-`<img>` rationale, vendoring a
  few Bootstrap Icons SVGs as local files rather than bundling the icon font, why `icon`
  stayed optional at the loader level, the card+result-grid-only scope, the PDF's
  duplicated CSS, and the grid icons' `currentColor` inheritance.
- Both docs' existing pre-existing drift (e.g. `loader.py`'s relationship fields are still
  literally named `brethren`/`besties`/`battlers` even though `CONTEXT.md` describes a
  backlog-#0004 rename to `natural_allies`/`friends`/`necessity`) was **not** touched —
  that's a pre-existing inconsistency unrelated to this change, out of scope here.

## CHANGELOG.md

Added one `Unreleased` bullet (feature) describing the icon delivery mechanism, the new
`icon` schema field, the loader validation, the two templates touched, and the
CSS/PDF-duplication approach — following the file's existing bullet style and phrasing.

## Verification performed

- `pytest` — 247 passed (unchanged from before this change; no new tests added by the
  coder — the spec's "Tests" section explicitly scopes test-writing to the Tester stage).
- `load_survey('content/survey.yaml')` directly — confirmed all 9 personas resolve a
  non-empty `icon` path.
- Rendered `_persona_card.html` and `_result_grid.html` directly via the Jinja env with the
  real survey's personas — confirmed inline `<svg` markup appears in both, and that a
  fixture persona with no `icon` renders no `persona-icon` span at all (no empty markup).
- Called `app/pdf_utils.py::generate_result_pdf` directly (WeasyPrint) — confirmed it
  still generates a valid PDF with the new inline `<style>` block present.

## What the Tester should focus on

1. **Web result page**: persona card shows the icon next to the persona name (all 9
   persona ids), and the result grid shows an icon above the name in every one of the 9
   cells, correctly stacked (icon above text).
2. **Selected vs muted grid-cell icon colour**: the icon in the selected (green) cell
   should read white; icons in the 8 muted cells should read grey — both via inherited
   `currentColor`, not an explicit rule.
3. **PDF parity**: the downloaded PDF's persona card also shows the icon (same green as
   web), sized correctly — this is the one surface with duplicated CSS, most likely to
   drift out of sync with `theme.css` in future changes.
4. **Graceful degradation**: the 3 small test fixtures (`survey_min.yaml`,
   `survey_audience.yaml`, `survey_grid.yaml`) have no `icon` field — confirm those flows
   still render (no error, no empty icon span) since none of their personas set one.
5. **Loader validation**: `icon: ""` or `icon: 123` on a persona should raise
   `SurveyConfigError`; omitting `icon` entirely should load fine.
6. **Real-survey completeness**: per the spec's recommended test, confirm all 9 personas
   in `content/survey.yaml` (the actual production content) have a non-empty `icon` — this
   guards content completeness even though the schema doesn't force it.
7. Confirm `_question_grid.html` (question-time grid) and `templates/email/*` were not
   touched and don't show icons — both are explicitly out of scope per the spec.

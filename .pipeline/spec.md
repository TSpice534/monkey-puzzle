# Spec — #0005 Vector icons for persona cards and result grid

Branch: `feature/persona-icons` (base `dev`).

Add a simple line-art SVG icon per persona, shown (1) next to the persona name on the
persona card and (2) in each labelled result-grid cell. One icon file per persona id,
inlined into the HTML so it renders identically in the browser and the WeasyPrint PDF.

## OPEN QUESTIONS

None. The two Tom-confirmed decisions (SVG-per-persona file; scope = card + result grid
only, NOT the question-time grid) are settled. One deliberate implementation choice is
flagged inline (loader validation kept *optional* rather than *required* — see "loader.py"),
with rationale; build it as written.

## Scope guardrails

- Touch ONLY the persona card (`_persona_card.html`) and the labelled result grid
  (`_result_grid.html`). Do NOT touch `_question_grid.html` — it stays blank-until-answered.
- Do NOT touch email templates (`templates/email/*`) — they don't include the persona card,
  same pre-existing gap as the relationships/innovation copy. Out of scope.
- No new Python deps, no DB/model changes, no migration. Bootstrap Icons stays a CDN asset;
  we vendor a few of its SVGs as local static files — we do NOT start bundling the icon font.

## Delivery mechanism (read first — it drives everything)

The established pattern for graphics here is to **inline SVG markup** into the template via
`{{ ... | safe }}` (see `fingerprint_svg` in `survey/result.html:27` and `pdf/result.html:58`).
Do the same for persona icons — do NOT use `<img src=...>` or `url_for('static', ...)`
references, because:
- The PDF is rendered in-process by WeasyPrint; a URL-referenced image forces an HTTP
  round-trip back to the server (fragile / can hang the dev server).
- CSP is `img-src 'self' data:` (`app/__init__.py:67`). Inline `<svg>` is DOM, not an image,
  so it's unaffected by CSP and needs no nonce. Keep it that way — no inline `<style>`/
  `<script>` inside the icon SVGs.

Inlining is done by a small Jinja global `persona_icon(persona)` that reads the persona's SVG
file off disk once (cached) and returns it as safe `Markup`.

## Files to create

### `app/static/icons/<id>.svg` — 9 files

One per persona id (confirmed against `content/survey.yaml`):
`accountant`, `implementer`, `developer`, `advocate`, `communicator`, `activist`,
`connector`, `cooperator`, `entrepreneur`.

Placeholder line-art. Source each from **Bootstrap Icons 1.11.3** (the version loaded in
`base.html:11`; MIT-licensed) using this suggested mapping, or equivalent simple line-art:

| persona | Bootstrap icon |
|---|---|
| accountant | `calculator` |
| implementer | `tools` |
| developer | `code-slash` |
| advocate | `megaphone` |
| communicator | `chat-dots` |
| activist | `lightning-charge` |
| connector | `diagram-3` |
| cooperator | `people` |
| entrepreneur | `rocket-takeoff` |

Each file MUST conform to this root-element contract (so sizing/colour is CSS-driven and
swapping in final custom art later is a pure file replacement — no template change):

```html
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" focusable="false">
  <path d="…"/>
</svg>
```

File-content rules:
- Keep `viewBox="0 0 16 16"` and `fill="currentColor"` (colour then inherits from CSS `color`).
- NO `width`/`height` attributes (CSS controls size), NO `class`, NO inline `style`, NO `<script>`.
- `aria-hidden="true"` + `focusable="false"` — the persona name sits right next to it, so the
  icon is decorative and must not be announced or focusable.

### `app/survey/icons.py` — the inlining helper

```python
"""Inline persona icon SVGs into templates.

A persona's `icon` (content/survey.yaml) is a path relative to the Flask
static folder (e.g. 'icons/developer.svg'). We inline the file's SVG markup
directly — same approach as the fingerprint radar — so it renders identically
in the browser and in the WeasyPrint PDF without any HTTP round-trip or CSP
img-src grant. Content is trusted (owned by Rob/Andrew), not user input.
"""
import os

from flask import current_app
from markupsafe import Markup

_cache = {}  # keyed by static-relative icon path -> raw SVG string


def persona_icon(persona: dict) -> Markup:
    """Return the inlined SVG markup for `persona`, or empty Markup if the
    persona has no `icon` or the file is missing (renders nothing, never errors)."""
    icon = (persona or {}).get('icon')
    if not icon:
        return Markup('')
    if icon not in _cache:
        path = os.path.join(current_app.static_folder, icon)
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                _cache[icon] = fh.read().strip()
        except OSError:
            _cache[icon] = ''
    return Markup(_cache[icon])
```

## Files to modify

### `content/survey.yaml`

Add an `icon:` field to each of the 9 `personas:` entries, value = path relative to the
static folder. Example for the `developer` block:

```yaml
  developer:
    name: "The Developer"
    tagline: "You build the thing that doesn't exist yet."
    icon: "icons/developer.svg"
    …
```

Do this for all 9 (`icons/accountant.svg`, `icons/implementer.svg`, … `icons/entrepreneur.svg`).
Path is static-relative (resolves on disk to `app/static/icons/<id>.svg`) — the idiomatic
Flask convention; keep the value in sync with the filenames you create. Place `icon:` near the
top of each persona block (e.g. after `tagline`).

Note on the decision: the confirmed decision wrote the example as `app/static/icons/developer.svg`.
Store it static-relative (`icons/developer.svg`) instead — it's the same file, referenced the
idiomatic Flask way so the helper resolves it via `current_app.static_folder`. Intent (one SVG
file per id, swap by replacing the file, no template rework) is unchanged.

### `app/survey/loader.py` — `_validate_personas`

Validate `icon` as an **optional** non-empty string (mirror the `label_organisation`
optional-string check at loader.py:211-217). Inside the `for persona_id, persona in
personas.items()` loop, after the required-field loop (loader.py:76-78), add:

```python
        icon = persona.get('icon')
        if icon is not None and (not isinstance(icon, str) or not icon):
            raise SurveyConfigError(
                f"persona '{persona_id}' field 'icon', if present, must be a non-empty string"
            )
```

Rationale for optional (NOT adding `icon` to the required `('name','tagline','description')`
tuple): CLAUDE.md forbids making a persona field required without also updating every fixture
(`survey_min.yaml`, `survey_audience.yaml`, `survey_grid.yaml`) and the `_base_config()` builder
in `tests/test_loader.py:25`. Optional keeps that churn to zero, `persona_icon()` degrades
gracefully when a persona has no icon, and completeness of the *real* survey is guarded by a
dedicated test (see Tests). Do NOT touch `_normalise` — no default needed.

### `app/__init__.py` — register the Jinja global

Import and register the helper so both the browser render and the WeasyPrint PDF render (same
Jinja env) can call it. Add after the blueprint registrations (~line 39):

```python
    from app.survey.icons import persona_icon
    app.jinja_env.globals['persona_icon'] = persona_icon
```

### `app/templates/survey/_persona_card.html`

Render the icon before the persona name in the `<h1>` (currently line 6:
`<h1 class="h3">{{ persona.name }}</h1>`). Guard on `persona.icon` so personas without one
(fixtures) render no empty span:

```html
    <h1 class="h3">
      {% if persona.icon %}<span class="persona-icon persona-icon--card">{{ persona_icon(persona) }}</span> {% endif %}{{ persona.name }}
    </h1>
```

`persona_icon()` returns `Markup`, so NO `| safe` filter is needed. This partial is included
verbatim by both `survey/result.html` (web) and `pdf/result.html` (WeasyPrint) — the icon must
show in both. See the PDF `<style>` change below.

### `app/templates/survey/_result_grid.html`

In each cell (currently lines 30-32), render the persona icon above the name. Guard on
`cell_persona.icon`:

```html
                <div class="grid-cell grid-cell--result {{ 'grid-cell--selected' if is_selected else 'grid-cell--muted' }}">
                  {% if cell_persona.icon %}<span class="persona-icon persona-icon--grid">{{ persona_icon(cell_persona) }}</span>{% endif %}
                  {{ cell_persona.name }}
                </div>
```

Grid icons intentionally inherit `currentColor` (no `--card` colour override) so they read
white in the selected cell and muted-grey in muted cells, matching existing cell text colours.

### `app/templates/pdf/result.html` — inline `<style>` block

The PDF template does NOT load `theme.css` (only Bootstrap CDN + its own inline `<style>`), so
the persona-icon CSS must be duplicated into its `<style>` block (same reason `.chart-col svg`
sizing lives there). The PDF shows the persona card only — it does NOT include
`_result_grid.html` — so only the card rules are needed. Add to the `<style>` block:

```css
    .persona-icon { display: inline-block; line-height: 0; vertical-align: middle; }
    .persona-icon svg { display: block; width: 100%; height: 100%; }
    .persona-icon--card { width: 1.6rem; height: 1.6rem; color: #2e7d32; }
```

(Hex `#2e7d32` = `--brand-primary`; the PDF style block uses literal hex elsewhere since the
theme.css custom properties aren't loaded here.)

### `app/static/css/theme.css` — web sizing/colour

Append a persona-icon section (after the grid rules, ~line 113):

```css
/* Persona icons (backlog #0005) — inline SVG marks on the persona card
   heading and each labelled result-grid cell. SVG files carry no intrinsic
   size; sized here. Colour inherits via currentColor except on the card. */
.persona-icon {
  display: inline-block;
  line-height: 0;
  vertical-align: middle;
}
.persona-icon svg {
  display: block;
  width: 100%;
  height: 100%;
}
.persona-icon--card {
  width: 2rem;
  height: 2rem;
  color: var(--brand-primary);
}
.persona-icon--grid {
  width: 1.5rem;
  height: 1.5rem;
}
```

Also modify the existing `.grid-cell--result` rule (theme.css:91-94) to stack the icon above
the name (add `flex-direction` + `gap`; the cell is already `display:flex` centred):

```css
.grid-cell--result {
  flex-direction: column;
  gap: 0.25rem;
  font-weight: 600;
  font-size: 0.9rem;
}
```

Known cosmetic (do NOT "fix"): in the selected result cell, the existing
`.grid-cell--selected::before` checkmark (theme.css:104-107) becomes the first item in the
now-column flex, so it sits above the icon. Acceptable.

## Edge cases the implementation must handle

- **Persona with no `icon` (fixtures / older content):** `persona_icon()` returns empty
  `Markup`; templates additionally guard with `{% if persona.icon %}` so no empty `<span>` is
  emitted. No error.
- **Icon file missing on disk:** `persona_icon()` swallows `OSError` and returns empty `Markup`
  (never 500s a result page over a missing decorative asset).
- **Web vs PDF parity:** the card icon must render in both — web gets its CSS from `theme.css`,
  PDF from its own inline `<style>` (both edited above).
- **Selected/muted grid cell colour:** grid icons must inherit cell text colour (white when
  selected, grey when muted) — achieved by NOT setting `color` on `.persona-icon--grid`.
- **Autoescaping:** helper returns `markupsafe.Markup`, so the raw `<svg>` is not HTML-escaped;
  do NOT also apply `| safe` (avoids confusion, not double-escaping).

## Patterns to follow

- Inline-SVG-into-template: `render_fingerprint_svg` usage in `survey/result.html` +
  `pdf/result.html`.
- Optional non-empty-string field validation: `label_organisation` check in `loader.py:211-217`.
- PDF-has-its-own-CSS: `.chart-col svg` rule inside `pdf/result.html`'s `<style>`.

## Tests (for the Tester stage)

Add to `tests/test_loader.py` (mirror persona-field tests ~lines 186-200):
- `icon` present but empty string / non-string → `SurveyConfigError`.
- `icon` absent → still loads fine (asserts the field stays optional).
- Real-survey completeness: `load_survey(REAL_SURVEY_PATH)` yields a non-empty string `icon`
  for every one of the 9 personas (guards that real content has all icons even though the
  schema doesn't force it).

Recommended render coverage (use the real survey path — fixtures have no icons): assert the web
result page and the downloaded PDF contain inline `<svg` markup from the persona icon.

## Post-task (per CLAUDE.md)

Add one bullet to the `Unreleased` section of `CHANGELOG.md` describing the change. Do NOT bump
`VERSION`. Do NOT `git add` CLAUDE.md / CONTEXT.md. No AI-attribution commit trailer (public repo).

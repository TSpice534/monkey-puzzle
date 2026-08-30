---
id: 0032
title: Hover/tap popup with persona summary on result-page grid cells
type: feature
status: todo
created: 2026-08-30
branch:
---

## Request
When hovering over a cell in the persona grid on the results page, show a brief summary
of that persona/role in a floating popup.

## Investigation
**Grid markup** (`app/templates/survey/_result_grid.html`): 9 cells, each a `<div
class="grid-cell grid-cell--result ...">` inside a `<td>`, rendering `cell_persona.icon`
(if present) + `cell_persona.name`. No `title`/`data-bs-*` attributes today, no per-cell
interactivity beyond the existing `:hover` border-colour rule (`theme.css:126-128`,
`.grid-cell:hover { border-color: var(--brand-primary); }`).

**Bootstrap tooltip availability**: `bootstrap.bundle.min.js` (includes Popper) is already
loaded in `base.html:56`, but nothing in the codebase currently initialises a Bootstrap
Tooltip or Popover — `data-bs-toggle="alert"`/`data-bs-dismiss` (flash messages) is the
only existing `data-bs-*` usage, and tooltips/popovers need an explicit JS init call
(`new bootstrap.Tooltip(el, {...})` per element, or a loop over
`document.querySelectorAll('[data-bs-toggle="tooltip"]')`) — Bootstrap does not
auto-initialise them. This would be a new inline `<script>` in `result.html`'s `{% block
scripts %}` (calling `{{ super() }}` first, per the rule in `CLAUDE.md`'s Templates
section), following the same nonce'd-inline-script precedent as
`_question_profile_pair.html`'s live-sentence updater and `result.html`'s existing
copy-caption button script (backlog #0017 Part B, #0030) — needs `nonce="{{ csp_nonce }}"`
to satisfy the CSP (`g.csp_nonce`/`_inject_csp_nonce` in `app/__init__.py`), no
`'unsafe-inline'`.

**Content available per persona** (`content/survey.yaml`, backlog #0004 copy): `tagline`
(audience-neutral) and `description`/`description_organisation` (audience-aware), same
fields `_persona_card.html` already renders via the `persona_description(persona,
audience)` macro (`app/templates/survey/_macros.html`). `_result_grid.html` doesn't
currently receive `audience` explicitly, but it's `{% include %}`-d from `result.html`
which does have it in scope (Jinja includes share the parent template's context by
default) — so the macro can be reused as-is for the popup body.

**Touch/mobile**: `theme.css:330-334` already has the app's one mobile breakpoint
(`@media (max-width: 767.98px)`), shrinking the grid. Bootstrap 5.3 tooltips fire on
`hover focus` by default; on touch devices most mobile browsers translate a tap into a
synthetic hover/focus, but this should be verified manually on a real touch viewport once
built, not assumed — Popper's auto-flip/placement also needs checking at the grid's small
mobile cell size so the popup doesn't overflow the viewport edge.

**Accessibility**: cells are plain `<div>`s, not focusable — for keyboard users to reach
the same popup via focus (not just mouse hover), each cell likely needs `tabindex="0"` and
a `role`/`aria-describedby` wired to the tooltip content, consistent with the
`aria-live`/`role="radiogroup"` care already taken elsewhere in this app (`step.html`,
`_question_profile_pair.html`).

## Notes
Resolved with Tom at filing time:
- **Popup content**: tagline **and** the fuller audience-aware description (via the
  existing `persona_description()` macro), not tagline alone.
- **Touch devices**: tap-to-toggle should work, not a desktop-only feature — whoever ships
  this should verify Bootstrap's default tap-as-hover/focus behaviour actually surfaces the
  popup on a real touch viewport, and adjust (e.g. explicit `trigger: 'click'` on touch) if
  it doesn't.

Open questions for whoever ships this (`/ship #0032`):
- Bootstrap Tooltip (single-line-ish, simpler) vs Popover (built-in title+body split,
  better suited to "tagline + description" as two visually distinct parts) — Popover looks
  like the better fit given the resolved content scope, but worth confirming against how
  it actually renders at grid-cell size.
- Exact popup placement/behaviour on the selected cell (the respondent's own persona) —
  should it show the same popup as the other 8, even though that persona's full card is
  already below on the page?
- Keyboard-focus/tabindex wiring for accessibility (see Investigation above) — not
  optional given this app's existing WCAG care (`base.html`'s skip link, `aria-live`
  regions), but the exact markup pattern is a call for implementation time.

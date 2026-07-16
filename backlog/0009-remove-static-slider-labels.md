---
id: 0009
title: Remove static labels from sliders, show only the live label
type: change
status: in-progress
created: 2026-07-16
branch: feature/spectrum-slider-labels
---

## Request
Remove the static row of all option labels under spectrum sliders; keep only the live/current
label that updates as the slider is dragged.

## Investigation
Both label rows live in `app/templates/survey/_question_spectrum.html`:

- **Live label** (to keep) — lines 18-20: `<span id="{{ question.id }}_current_label">{{
  ns.labels[current_index] }}</span>`, server-rendered on load to the current/default value, then
  updated on drag by the inline script in `app/templates/survey/step.html` (lines 42-57, the
  project's one deliberate bit of JS — a progressive-enhancement pattern chosen in Phase 3
  specifically to avoid Alpine.js/`'unsafe-eval'` under the CSP).
- **Static label row** (to remove) — lines 21-25: a `d-flex justify-content-between` row looping
  `ns.labels` and printing every option's label underneath the slider, always visible.

`ns.labels` (lines 3-6) is built once and used by *both* rows plus the `data-labels` JSON
attribute (line 17) that feeds the JS. Removing the static row (lines 21-25) doesn't let
`ns.labels` itself be deleted — it's still needed for `data-labels` and the initial live-label
value. This is purely a template-markup removal, not a data-model change.

**Interaction with backlog #0008** (open, not yet built): the live label is exactly the one
#0008 is fixing (it currently renders apostrophes as literal `&#39;` due to double HTML-escaping
through the `tojson`/JSON/`textContent` path — see that item for the full diagnosis). Once the
static row is removed, the live label becomes the *only* place the label text is shown, so
#0008's bug becomes more visible until fixed. Not a blocker for filing this item, but ideally
#0008 ships first or alongside.

**Accessibility/no-JS note:** `_question_spectrum.html`'s own comment (lines 7-10) states the
static row exists partly so "the widget degrades gracefully" when JS is off — without it, a
JS-disabled user loses visibility into every option's label while dragging (though the initial
label still renders server-side, and the native `<input type=range>` still submits a valid index
either way — no functional/submission breakage, just reduced label visibility while adjusting).

## Notes
- Sequence with #0008 if possible — the live label is the sole surviving label after this ships,
  so its apostrophe-escaping bug becomes more visible in the meantime.
- The no-JS label-visibility trade-off above is worth a quick sanity check with Tom during
  `/ship`, but isn't blocking — he's explicitly asked for this simplification.

---
id: 0008
title: Apostrophe renders as &#39; in spectrum slider live label
type: bug
status: shipped
created: 2026-07-16
branch: feature/spectrum-slider-labels
---

## Request
Apostrophes aren't rendering properly in the dynamic slider label / survey answers — they show
up as the literal text `I&#39;m` instead of `I'm`. Seen on Q4 "How ambitious are you?": the live
label above the slider shows `I&#39;m keeping pace with those around me`, while the identical
option text in the static row underneath renders correctly as `I'm keeping pace with those
around me`.

## Investigation
Two paths render the same option label text on the spectrum-slider widget, and only one breaks:

1. **Static label row** (`app/templates/survey/_question_spectrum.html:22-24`) — plain Jinja
   `{{ label }}` in a normal HTML context. Correct.
2. **JS-driven live label** — the same text is captured into `ns.labels`
   (`_question_spectrum.html:5`), serialized with `data-labels='{{ ns.labels | tojson }}'`
   (line 17), read by `step.html`'s inline script via `JSON.parse(input.dataset.labels)`, and
   written via `labelEl.textContent = ...` (`step.html:51`). Broken.

The label text originates from the `option_label(option, audience)` macro
(`app/templates/survey/_macros.html:4-6`), whose body is `{{ option.label_organisation if ...
else option.label }}`. Because Jinja autoescaping is on for `.html` templates, that `{{ }}`
inside the macro HTML-escapes the raw text at macro-render time — an apostrophe becomes the
literal 6 characters `&#39;`. Jinja marks a macro's return value as `Markup` (safe), which is
correct for path 1: interpolating that Markup back into HTML via `{{ label }}` lets the
browser's HTML parser decode `&#39;` back into `'` when it builds the DOM.

Path 2 breaks because the value never goes through an HTML parser again: `tojson` serializes
the already-entity-encoded text into a JSON string (the literal characters `&#39;`, not a real
apostrophe — JSON doesn't know about HTML entities), `JSON.parse` hands that literal string
straight to JS, and `textContent` writes it into the DOM as plain text (not parsed as HTML), so
`&#39;` displays verbatim instead of being decoded.

In short: the label text is HTML-escaped once correctly (inside the macro, for path 1), but
that escaped text then leaks into a non-HTML sink (JSON → JS → `textContent`) that never
reverses the escaping.

**Likely fix shape** (for `/ship`'s planner/coder to design, not decided here): `ns.labels`
(used for the JSON payload) needs the raw, un-escaped label string — built from
`option.label_organisation if audience == 'organisation' and option.label_organisation else
option.label` directly (a `{% set %}` on the raw dict value, no macro call, so autoescape never
touches it) rather than routing through `option_label(...)`. Flask's `tojson`
(`htmlsafe_json_dumps`) already unicode-escapes `<`, `>`, `&`, `'` for safe embedding in an HTML
attribute, so feeding it the raw string is the correct input — no manual escaping needed. The
static row (path 1) should keep using `option_label(...)` unchanged. Likely touches only
`app/templates/survey/_question_spectrum.html` (~lines 1-6, the `ns.labels` construction) — the
macro itself is fine and used correctly elsewhere; no reason to change it.

## Notes
- Check whether the `triangle` widget's corner labels, or any other JS-consumed `data-*`
  attribute, follow the same `option_label(...) | tojson` pattern — if so they'd have the
  identical latent bug. Not confirmed here; worth a grep in the coder stage.

---
id: 0043
title: Landing page: persona grid first, then title and description
type: change
status: shipped
created: 2026-09-28
branch: quickship/landing-page-persona-grid-first
---

## Request

Design tweak on the landing page. Reorder it to match the attached mockup:

1. Heading: "One of these is you"
2. The 9 persona icons + names (as they currently sit at the bottom of the page), moved to the top
3. Heading: "The Monkey Puzzle"
4. Paragraph: "Complete this short survey to receive your personalised profile around how you or your organisation are currently approaching sustainability!"
5. Button: "Begin"

Mockup: both headings large and bold, persona grid in a 4 / 4 / 1 layout (Accountant, Implementer, Inventor, Architect / Communicator, Advocate, Connector, Cooperator / Entrepreneur), green Begin button centred below the paragraph.

## Investigation

Sourced from project docs plus a read of `index.html` and `theme.css`.

- Landing page is `app/templates/index.html` (main blueprint). Current order: `<h1>` "The Monkey Puzzle", `<p class="lead">` copy (from #0016), green Begin button, then (added by #0042) a small muted "One of these is you" label and `<ul class="persona-preview-grid">`. This is mostly a reorder plus restyle of existing markup, not new content.
- Files likely touched:
  - `app/templates/index.html`: reorder blocks, promote "One of these is you" to a display-size heading, replace the lead paragraph copy.
  - `app/static/css/theme.css`: `.persona-preview-grid` (~line 301) is `flex-wrap`, centred, 1.25rem gap, so row breaks depend on viewport. The mockup shows a deliberate 4 / 4 / 1 layout, so the grid needs a `max-width` of about four items to force that wrap. Mobile tweaks go inside the existing final `@media (max-width: 767.98px)` block, which must stay the last block in the file (`tests/test_mobile_responsive_layout.py` asserts this).
  - `tests/test_persona_identity_in_survey_flow.py` (~lines 124-148): home page tests assert "One of these is you" and `persona-preview-grid`. Update if they check ordering or the old copy.
- Reuse: existing `persona_icon()` Jinja global and `.persona-icon--preview` class. Icon size may need a small tweak to match the mockup.
- Keep the `{% if personas %}` guard (page must still render if `survey.yaml` fails to load). Put the "One of these is you" heading inside the guard so it disappears with the grid, leaving "The Monkey Puzzle" + copy + Begin.
- On ship, also update the `index.html` description in CLAUDE.md/CONTEXT.md (local only) and add a CHANGELOG Unreleased bullet.

## Notes

- The new paragraph **replaces** the #0016 copy ("This short survey is designed to help you capture a snapshot..."). The mockup drops the "results that you can share" line. Treated as a straight replacement since the mockup is explicit.
- The mockup shows "One of these is you:" with a trailing colon, the request text has none. Default to the request text (no colon); confirm with Tom if it matters.
- Heading semantics: recommend keeping `<h1>` on "The Monkey Puzzle" (page identity) and styling "One of these is you" as a large `<h2>`, even though it now appears first visually. Decide at ship time.
- Small template + CSS change: `/quick-ship` is probably enough, no need for the full `/ship` pipeline.

---
id: 0042
title: Carry some of the result page's visual identity into the survey flow
type: change
status: todo
created: 2026-09-23
branch:
---

## Request

The result page has real visual personality (the 9 hand-styled persona icons, the colour-coded
relationship grid, the innovation-curve bell chart, the certificate download), but the home page
and all 11 survey steps are plain, generic Bootstrap: white card, one green accent, system sans
serif, no imagery. For a tool designed to be taken once and shared/re-taken virally, all of the
personality is currently banked for the very end — nothing earlier builds anticipation or
reinforces "this is The Monkey Puzzle" while someone's actually answering questions.

Suggestion (not a fixed spec — needs a design pass, not just an implementation): work some of the
persona icon set or the brand green more visibly into the survey-taking steps themselves, e.g. a
subtle icon treatment on the progress bar, or icon hints tied to which persona each answer leans
toward. Should stay tasteful and not spoil/hint at the result before the end.

## Investigation

Originally sourced from an `apple-design` skill design review's craft lens ("is it a template?
does it have a point of view throughout, not just at the end?") — a design-direction suggestion,
not a located bug, with no specific files or spec identified.

**Follow-up (2026-09-23):** Tom asked to brainstorm a concrete direction, grounded in the
`apple-design` skill's HIG references (`design-principles.md`, `branding.md`, `onboarding.md`,
`progress-indicators.md`, `icons.md`, `motion.md`, `cross-platform.md` — read directly, not from
memory) rather than left as an open suggestion. Two things came out of that pass that make this
ready to scope for `/ship`:

**Technical constraint that shapes the whole design:** `content/survey.yaml` (the real survey)
has zero `weights:` keys anywhere — persona is resolved exclusively by the `profile_matrix`
construct at the combined step 7, not incrementally through earlier questions. There is no
per-question persona signal before that step, so any pre-resolution treatment must be generic
(not persona-specific), or it either spoils the result early or fakes a signal that doesn't exist.

**Second constraint, found by reading `app/survey/routes.py::step` (line ~292):** even though
step 7's answers *mathematically* determine the persona, the code doesn't actually call
`classify_submission()` / store `submission.persona_id` until the respondent submits the final
step (`step == total`, the `why_reason` step) — persona isn't computed early today. Good news:
`classify_submission(answers, survey)` (`app/survey/persona.py`) is a pure function of
`submission.answers` and `survey`, both already in scope in `_render_step()`
(`app/survey/routes.py:183`) — so showing the resolved persona on steps 8-11 only needs an extra
*display-only* call to `classify_submission()` inside `_render_step()` for steps after the
profile step, not a DB/schema change and not touching when `submission.persona_id` actually gets
persisted (that stays at true completion, unchanged).

**Recommended direction** (this replaces "needs a design pass" — treat this as the spec):

- **Signature moment — the step 7→8 transition ("the reveal").** Brief (~300ms), purposeful CSS
  transition when the persona icon first appears, not an abrupt reload — the app is literally
  called The Monkey Puzzle, and step 7 is the moment the puzzle resolves. One deliberate motion
  investment, nowhere else (`motion.md › Best practices`: avoid motion on frequent interactions;
  steps 1-7 are frequent, this transition happens once). Must degrade to an instant snap under
  `@media (prefers-reduced-motion: reduce)` — pure CSS, no JS, matching the survey pages' existing
  scriptless approach.
- **Pre-resolution (home page + steps 1-7) — quiet and generic, no spoiler risk.** Home page: a
  static, undifferentiated grid of all 9 persona icons (loop `config['personas']` through the
  existing `app/survey/icons.py::persona_icon()` helper — no new assets needed), "one of these is
  you," nothing highlighted, no motion. `_progress.html` could optionally get section-level copy
  instead of/alongside "Question X of Y" — content-only change, no persona reference. No
  color/icon-per-answer anywhere before step 8: nothing to base it on, and it would spoil the
  result.
- **Post-resolution (steps 8-11 + result page) — content-layer accent, not chrome.** Small
  persistent persona icon badge (header/progress area) from step 8 onward, using the
  display-only `classify_submission()` call above; same icon/colour continues into the existing
  result-page persona card for continuity (`design-principles.md › Familiarity`: "preserve a
  person's context... keep content and controls in consistent, predictable positions"). Persona
  colour stays in the badge/content layer, not buttons/chrome — keeps `--brand-primary` as the
  one UI accent (`branding.md › Best practices`: "apply your accent color judiciously... consider
  moving it into the content layer").
- **Accessibility guardrails — don't regress #0039-#0041's fixes.** Icon + persona name together,
  never colour alone, as the identity signal (same reasoning as #0039's contrast fix). Whatever
  colour the post-resolution badge uses needs the same 4.5:1 contrast check #0039 applied, now
  across up to 9 persona colours instead of one green. Motion optional per above.

Files likely touched: `app/templates/index.html` (icon grid), `app/templates/survey/_progress.html`
(reveal transition + persona badge from step 8, possibly section copy), `app/templates/survey/step.html`
(badge placement), `app/static/css/theme.css` (transition + reduced-motion fallback + badge/contrast
styling), `app/survey/routes.py::_render_step` (display-only `classify_submission()` call for
steps after the profile step).

## Notes

Originally filed as the lowest-priority, "worth Tom/Rob/Andrew's call" item from the design
review. Tom has since confirmed (2026-09-23) he wants to move forward with the direction above —
that priority framing is stale; see Investigation for the concrete, ship-ready spec.

Keep this to the one signature moment (the step 7→8 reveal) — resist expanding into per-step
animation or persona colour changes on every screen. That dilutes the one earned moment and risks
the generic/templated look the original design review's craft lens warned against (`design-
principles.md › Delight`: "don't mistake delight for decoration").

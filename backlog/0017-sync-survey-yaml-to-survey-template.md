---
id: 0017
title: Sync survey.yaml to updated docs/SURVEY-TEMPLATE.md (Parts A+B)
type: feature
status: shipped
created: 2026-08-04
branch: feature/profile-grid-to-single-select
---

## Phasing

Split into two independent parts (confirmed with Tom 2026-08-04):
- **Part A (shipped 2026-08-04)**: items 3–6 — reword `space_to_progress`/
  `support_type`/`target_groups`, add Explanation help-text to `space_to_progress`,
  `need_most`, `have_enough`, `support_type`. Content-only for 3 of 4 questions; adding
  Explanation was a new schema concept (loader had no generic help-text field for
  `spectrum`/`triangle` questions) — landed as a new optional `explanation` field
  (not a reuse of `instructions`, which was already overloaded). Reviewer verdict: SHIP.
  Merged `feature/survey-copy-and-explanations` into `dev` and pushed 2026-08-04.
- **Part B (shipped 2026-08-04)**: item 7 — replaced `profile_grid` widget with two
  single-select questions (`profile_approach`/`profile_scope`), resolved via a new
  `profile_matrix` construct. Kept the result-page 3x3 grid visualization per Tom's
  explicit call (reconstructed at render time via `_profile_grid_context()`, mapping
  `approach → y`, `scope → x`) rather than deleting it as originally scoped — spec was
  revised mid-flight after Tom's answer to that OPEN QUESTION. `type: grid` schema
  support removed entirely (confirmed unused elsewhere); `_question_grid.html` deleted;
  `_result_grid.html` unchanged. Tester independently re-derived all 9 persona-mapping
  cells against the retired grid on `dev` — exact match. Reviewer independently
  spot-checked the same. Reviewer verdict: SHIP. Branch
  `feature/profile-grid-to-single-select` off `dev`, not yet merged — Tom's manual
  review/merge. One non-blocking nit: `_result_grid.html`'s header comment still
  mentions the retired `profile_question` key (comment only, guard logic unaffected).
  Follow-up filed separately: **#0019** (`prompt_organisation` schema field — the
  org-register prompt variant from the template has no home; Part B used the single
  individual-register prompt for both tracks per Tom's call).

## Request

Tom rewrote `docs/SURVEY-TEMPLATE.md` (uncommitted local edit) and wants the changes
implemented into the running survey (`content/survey.yaml` and the code/templates
behind it).

## Investigation

Diffed the new (uncommitted) template against the old committed version and against
current `content/survey.yaml` (`git diff HEAD -- docs/SURVEY-TEMPLATE.md content/survey.yaml`).
Findings, in survey order:

1. **`why_reason` reworded + moved to end** — already covered by backlog **#0015**, filed
   separately this session. Not duplicated here.
2. **`motivation` "acceptation" option reworded** ("It is part of my role" → "I do only
   what is asked/required") — already applied to `survey.yaml` as an uncommitted edit.
   Nothing to do.
3. **`space_to_progress` rewritten** — new prompt ("What is the current balance between
   your commitments and capacity?"), all 5 option labels reworded and now
   audience-neutral (single wording, `label_organisation` should be dropped for this
   question), plus a new **Explanation** help-text value to display. Scores unchanged
   (1/3/5/3/1). Not yet applied.
4. **`need_most` / `have_enough`** — prompts/options unchanged; template adds an
   **Explanation** value for each (what capacity/knowledge/support mean). Not yet
   applied.
5. **`support_type` reworded** — prompt "What type of support do you desire?" → "What
   type of assistance do you desire?", plus a new Explanation value. Not yet applied.
6. **`target_groups` reworded** — prompt "What target groups would you like to
   collaborate with the most?" → "Who are you trying to work with?". Options/phrases
   unchanged. Not yet applied.
7. **Profile question restructured (biggest item)** — the old 3x3 grid (`profile_grid`,
   `type: grid`, Matrix format) is replaced by two sentence-completion rows: "Complete
   the following sentence: 'I want to...'" (options: "Create space to address the
   topic" / "Work to implement existing solutions" / "Test new ideas") and a second row
   ("Within my own organisation" / "Collaborating within my sector" / "Creating impact
   within wider society"), annotated in the template as "(second row of buttons ->
   eliminate the grid)". **Confirmed with Tom: this means replacing the interactive 3x3
   grid widget with two separate single-select button-row questions**, combined answers
   still resolving the same 9 personas.
   - Current implementation: `content/survey.yaml`'s `profile_grid` question
     (`x_axis`/`y_axis`/`cells`), resolved by `app/survey/persona.py::resolve_profile_persona`
     (lines 84-100), which reads one question id (`profile_question` top-level key)
     whose answer is a 2-element `[x, y]` list matched against `cells`.
   - Will need: two new `type: single` questions (reuse the existing single-select
     pattern from `respondent_type`/`target_groups`) replacing `profile_grid`; a
     loader schema change linking both question ids' selected option indices to the 9
     persona cells; `resolve_profile_persona` rewritten to read two answers instead of
     one list answer.
   - `_question_grid.html` becomes unused for this question. `_result_grid.html` (web
     result page) and any grid-specific rendering in `charts.py` (share image, etc.)
     assume a 3x3 grid visualization and need checking by whoever plans the build —
     not resolved here.

Source: docs-only (CLAUDE.md's Project Structure/Survey content sections plus the git
diff) except for `resolve_profile_persona`, read directly to confirm the current
data shape.

## Notes

- Classified `feature` (not `change`) because item 7 replaces a widget, not just
  copy — even though items 3–6 are simple rewording/help-text additions. `/ship` or
  `/backlog-plan` may want to phase this into more than one branch given the size.
- Cross-reference: don't duplicate #0015 (why_reason move) — that's already filed.
- `docs/SURVEY-TEMPLATE.md` itself is still an uncommitted working-tree change, separate
  from this backlog item; filing this didn't touch or commit it.
- Explanation/help-text is a new concept for `spectrum`/`triangle` questions — the
  loader doesn't currently have a generic field for it (only `multi_range`/`grid`
  support an `instructions` string). Whoever plans this should decide whether to reuse
  `instructions` or add a new field.

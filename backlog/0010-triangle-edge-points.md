---
id: 0010
title: Edge points on triangle questions (between-corner answers)
type: feature
status: shipped
created: 2026-07-16
branch: feature/triangle-edge-points
---

## Request
On the questions with triangle interfaces for answer selection, add points on the triangle
edges so users can select an option between those available on the corners. Confirmed with Tom:
picking an edge point resolves to both flanking corners' phrases, joined, in the Now/Next copy
(e.g. "...a good amount of capacity and knowledge") — not a brand-new authored third option.
This is what he meant by "2 answers being added to the now/next copy on the results page."

## Investigation
**Which questions are affected:** `have_enough` (output: now), `need_most` and `support_type`
(both output: next) — `content/survey.yaml:265-334`. These are the only 3 `type: triangle`
questions. Confirmed via grep that none of the three are consumed anywhere except
`resolve_now_next` (not persona scoring, not innovation-curve) — this is a self-contained,
low-blast-radius change.

**Current widget** (`app/templates/survey/_question_triangle.html`) — exactly 3 radio inputs,
one per option, fixed corner mapping by list position (`options[0]` → top, `[1]` → bottom-left,
`[2]` → bottom-right; enforced by the loader, `app/survey/loader.py:198-200`, "must have exactly
3 options"). Each radio's `value` is the option's flat index (0/1/2); styled via
`:checked`-sibling CSS (`app/static/css/theme.css:140-201`, `.triangle-node--top` /
`--bottom-left` / `--bottom-right`), no JS.

**Current data flow for a corner pick:** `app/survey/routes.py::_read_answer` (lines 59-64) reads
triangle answers the same as `single`/`spectrum` — `int(raw)`, a single option index. Persisted
as-is to `Submission.answers[qid]` (JSON, so no schema/migration constraint either way).
`app/survey/persona.py::resolve_now_next` (lines 165-206) dispatches on `question['type']`: today
triangle falls into the `else` branch (single int → one `_statement_phrase` lookup); `multi`/
`multi_exact` take the other branch (list of ints → one `_statement_phrase` per index → joined
via `_join_phrases`, the same helper that Oxford-comma-joins the 3 `topics` selections).

**Precedent to follow for encoding an edge pick — the `grid` question type already does exactly
this shape of thing:** `_read_answer`'s `grid` branch (routes.py:51-57) parses a submitted
`"x,y"` string into `[int(x), int(y)]`. The natural, minimal-diff design: give the 3 new edge
radio nodes a `value` of `"i,j"` (the two flanking corners' indices, e.g. `"0,1"` for the edge
between `options[0]` and `options[1]`) instead of a single int, and add a triangle-specific
branch to `_read_answer` that tries `int(raw)` first (corner) and falls back to splitting on `,`
into `[i, j]` (edge) — mirroring the grid branch almost line-for-line. **No new yaml authoring
needed** — a triangle's 3 edges are always the pairwise-adjacent corners `(0,1)`/`(1,2)`/`(2,0)`,
entirely positional, so this needs zero new content from Rob/Andrew.

**Resolution side:** `resolve_now_next`'s type-dispatch (persona.py:189-206) would need triangle
to handle *both* shapes — an `int` answer (corner, unchanged single-phrase path) or a 2-element
`list` answer (edge, join both flanking corners' `_statement_phrase` via the existing
`_join_phrases`, exactly like the `multi`/`multi_exact` branch already does). This is additive to
the existing dispatch, not a rewrite — likely just changing the `if question['type'] in ('multi',
'multi_exact')` condition to also match `triangle` when the answer is a list, falling through to
the existing `else` (single-int) path when it's an int.

**Widget/CSS:** 3 new tappable nodes at the triangle's edge midpoints, positioned between the
existing corner nodes — new `.triangle-node--edge-*` (or similar) CSS rules alongside the
existing `--top`/`--bottom-left`/`--bottom-right` ones (`theme.css:176-201`), and 3 more radio
inputs in `_question_triangle.html` with `value="{{ a.index }},{{ b.index }}"` for each adjacent
corner pair, labelled via a join of both corners' `option_label()` (e.g. "Capacity & Knowledge")
so the tappable target itself communicates what it means before it's picked.

## Notes
None blocking — the one real ambiguity (what an edge pick means for the copy) was resolved with
Tom before filing.

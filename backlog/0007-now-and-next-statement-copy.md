---
id: 0007
title: Now and Next statement copy
type: feature
status: todo
created: 2026-07-15
branch:
---

## Request
Copy for the two "Now"/"Next" narrative result statements:

**Now statement:**
Your current sustainability focus is [TOPIC SELECTION 1], [TOPIC SELECTION 2], and
[TOPIC SELECTION 3], where you feel you have a good amount of [capacity] OR [support] OR
[knowledge] to help achieve your goals.

**Next statement:**
In order to progress your ambitions, you are looking for more [capacity] OR [support] OR
[knowledge]. This could be achieved by accessing more [information] OR [training] OR
[mentoring] to address this challenge. In terms of collaboration ambitions, you are keen
to engage more [with your audience] OR [with suppliers] OR [with knowledge partners] OR
[with policy makers] OR [within your own organisation].

## Investigation
`monkey-puzzle/CLAUDE.md` already documents the hook this fills: `output`
(optional on any survey question) supports `innovation_curve` / `now` / `next` /
`profile_direct`, and states plainly that `now`/`next`/`profile_direct` "remain
schema-only, not yet consumed" (CLAUDE.md lines 198-201). Confirmed via grep across
`app/` and `docs/` — the only hit is the loader's `_VALID_OUTPUTS` set
(`app/survey/loader.py:12`); nothing resolves or renders these tags today.

`content/survey.yaml` already has the four questions this copy consumes, each tagged:
- `topics` (multi_exact, choose 3, `output: now`, survey.yaml:250-263) — the 3 topic
  selections for "Your current sustainability focus is [X], [Y], and [Z]".
- `have_enough` (triangle, `output: now`, survey.yaml:211-218) — capacity/knowledge/
  support, for "...where you feel you have a good amount of [capacity/support/knowledge]".
- `need_most` (triangle, `output: next`, survey.yaml:202-209) — capacity/knowledge/
  support, for "you are looking for more [...]".
- `support_type` (triangle, `output: next`, survey.yaml:265-272) — information/training/
  mentoring, for "accessing more [...]".
- `target_groups` (single, `output: next`, survey.yaml:274-283, already has
  `label_organisation` variants) — audience/suppliers/knowledge partners/policy makers/
  own organisation, for "engage more [...]".

The request maps 1:1 onto existing schema — this is the copy plus resolution/rendering
logic to finally consume `output: now`/`next`, not new survey questions.

**Pattern to follow:** backlog #0002 (Rogers' innovation curve) did this exact shape of
work for `output: innovation_curve` — see CLAUDE.md's "Innovation-curve scoring" (lines
202-219) and "Templates" (lines 242-249) sections:
- `app/survey/persona.py::resolve_innovation_curve` — resolution logic, called from
  `survey.step` alongside `classify_submission`.
- `Submission.innovation_band` / `Submission.innovation_score` — nullable columns added
  via Alembic migration to persist the resolved result.
- `app/survey/routes.py::_innovation_context` — builds the shared context dict consumed
  by all three result surfaces.
- `survey/_result_innovation.html` — shared partial, included on the web result page and
  `pdf/result.html`; email inlines its own markup instead (mirrored, not reused).
- All three surfaces guard on the context being `None` (older submissions / surveys
  without the config).

A Now/Next build would likely mirror this: a resolution function in `persona.py`, new
nullable `Submission` column(s) to persist the resolved sentences, a context builder in
`routes.py`, a new shared partial rendered on web + PDF + inlined separately in email,
plus deciding where the template *strings themselves* live — `content/survey.yaml` (like
`innovation_curve.bands` tagline/description, so Rob/Andrew can edit without a deploy) is
the pattern-consistent choice over hardcoding in Python/Jinja.

**Audience-awareness:** `target_groups` already carries `label_organisation` variants,
and the rest of the survey is audience-aware throughout (`option_label()`,
`persona_description()` macros). The Now/Next templates would need an "I/my" vs "we/our"
variant too, consistent with the rest of the copy.

## Notes
- Tom's draft had an apparent bracket typo after "TOPIC SELECTION 3" — closed it above;
  flagging in case the intent was different.
- Where the template strings live (survey.yaml vs. code) and exact grammar polish
  (Oxford-comma joining for 3 topics, sentence casing) are implementation decisions for
  `/ship` to work out against the `innovation_curve` precedent, not resolved here.

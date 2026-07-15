# Test Results — Backlog #0004: Real persona & innovation-curve copy

## Summary: ALL TESTS PASS

- Full suite: `pytest tests/` → **265 passed** (253 pre-existing/coder-added + 12 new,
  independent verification tests added by the Tester in
  `tests/test_persona_copy_verification.py`).
- No failures, no errors, no skips.

## Independent verification performed (beyond running the suite)

Drove real submissions through the app via the Flask test client (in-memory SQLite, real
`content/survey.yaml`) and inspected actual rendered output — web result page, `pdf/result.html`
(rendered directly and, separately, the real `/pdf` download parsed with `pypdf` for a manual
sanity check outside the committed suite), and both email templates.

1. **Two full personas' copy, both audience tracks, web + PDF** — Entrepreneur and Communicator,
   organisation vs individual. Correct `tagline`, correct `description`/`description_organisation`
   (and confirmed the *other* wording is absent), on both the web result page and the PDF render.
2. **Two-value relationship lists render both names, comma-separated** — Communicator
   (`natural_allies: [advocate, accountant]`, `friends: [connector, cooperator]`) on web result
   page and PDF: `"The Advocate, The Accountant"` / `"The Connector, The Cooperator"` both present,
   not truncated to the first value. (The coder's own tests only exercised Entrepreneur for this;
   added as a new test.)
3. **Laggard band tagline verbatim, including "Wanker"** — reached through a genuine low-scoring
   submission (accountant persona, modifier 0, all three innovation-curve questions left
   unanswered so each contributes 0 → `innovation_score == 0` → `Laggards` band), not just a
   hand-built fixture. Confirmed byte-for-byte on the web result page, the PDF render, and both
   email bodies (`.txt` and `.html`). Not softened or altered anywhere.
4. **Persona relationships confirmed absent from email** — rendered both `email/result.txt` and
   `email/result.html` with the real Entrepreneur persona (2-value relationships) and
   `audience='organisation'`: none of `Natural allies`, `Friends:`, `Necessities`, nor any related
   persona name, appear in either body. Matches the spec's explicit instruction that this stays a
   pre-existing web+PDF-only gap, not extended to email — confirmed unchanged, not a new regression.
5. **`description_organisation` fallback correctness**:
   - Un-routed case: POSTing step 1 (`respondent_type`) with no value leaves `submission.audience`
     as `None` for the rest of a real, completed flow (the router question isn't force-validated
     the way the grid/`multi_exact` steps are) — result page and PDF both render the individual
     `description` wording, not the organisation wording, and neither route errors.
   - Missing-field case: rendered the macro with a persona dict lacking `description_organisation`
     entirely, under `audience='organisation'` — falls back to `description` cleanly, no crash.
     (Currently none of the real 9 personas actually lack this field — all have it per the
     template — so this is a synthetic guard for the optional-field contract, not a real-data gap.)
6. **Full-repo grep for stray old field names** — `grep -rn "brethren|besties|battlers"` across
   `.py`/`.html`/`.yaml`/`.yml`, excluding `docs/`, `backlog/`, `.git/`: **zero hits**. The only
   remaining mentions repo-wide are in `CHANGELOG.md` (describing the historical rename itself),
   `backlog/0002-*.md`, `backlog/0004-*.md`, and this pipeline's own `.pipeline/*.md` — all
   expected, historical-record mentions, not live code/template/test references.
7. **Loader failure case** — confirmed (and added as a committed test) that an
   `innovation_curve.bands` entry missing `tagline` or `description`, or with either as an empty
   string, raises `SurveyConfigError`. The coder's own `test_innovation_curve_band_missing_field_raises`
   parametrize list in `tests/test_loader.py` only covers `name`/`min`/`max`/`colour` — it was never
   extended to the two newly-required fields, so this closes a real coverage gap (the loader code
   itself was already correct; only the test coverage was missing).

## New tests added (`tests/test_persona_copy_verification.py`)

| Test | Covers |
|---|---|
| `test_communicator_two_value_relationships_render_both_names_on_web_result` | Happy path — 2-value relationship rendering, web |
| `test_communicator_two_value_relationships_render_both_names_in_pdf` | Happy path — 2-value relationship rendering, PDF |
| `test_laggard_band_tagline_renders_verbatim_on_real_low_score_submission` | Edge case — Laggard tagline via real submission, web |
| `test_laggard_band_tagline_renders_verbatim_in_pdf` | Edge case — Laggard tagline, PDF |
| `test_laggard_band_tagline_renders_verbatim_in_both_email_bodies` | Edge case — Laggard tagline, email (.txt + .html) |
| `test_description_falls_back_correctly_when_router_question_is_skipped` | Edge case — audience None (un-routed), web + PDF, no crash |
| `test_persona_description_macro_falls_back_when_description_organisation_absent` | Edge case — macro fallback for personas without org wording |
| `test_email_bodies_never_render_persona_relationships` | Regression guard — relationships stay out of email |
| `test_innovation_curve_band_missing_tagline_or_description_raises` (x2, parametrized) | Failure case — loader rejects missing required band fields |
| `test_innovation_curve_band_empty_string_tagline_or_description_raises` (x2, parametrized) | Failure case — loader rejects empty-string band fields |

## Full suite run

```
$ pytest tests/ -q
........................................................................ [ 27%]
........................................................................ [ 54%]
........................................................................ [ 81%]
.................................................                        [100%]
265 passed in 6.82s
```

## Files touched by the Tester

- `/Users/tomspice/Projects/monkey-puzzle/tests/test_persona_copy_verification.py` (new) — 12
  tests as tabulated above. No production code was modified.

No issues found. Recommend proceeding to Reviewer.

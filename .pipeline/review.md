# Review — Backlog #0004: Real persona & innovation-curve copy

## VERDICT: SHIP

The code matches the spec precisely, the tests are meaningful (not superficial), and
all five orchestrator-flagged checks pass. One minor doc-drift nit in a gitignored
local file is noted below — it does not block the merge.

## What I verified

**Code vs spec — exact match.**
- `app/survey/loader.py`: relationship tuple renamed to `('natural_allies','friends','necessity')`;
  optional `description_organisation` validated with the same "non-empty string if present"
  shape as the existing `label_organisation` check (loader.py:216); band `tagline`/`description`
  now required non-empty strings; `_normalise` setdefaults renamed, `description_organisation`
  deliberately not defaulted so the macro fallback works. All correct.
- `persona_description(persona, audience)` macro (`_macros.html`) is byte-identical in
  semantics to `option_label`: `X_organisation if audience == 'organisation' and X_organisation
  else X`. Correctly covers `audience is None` (un-routed → falls back to `description`) and
  the missing-org-field case. Matches spec check #3 exactly.
- `routes.py` threads `submission.audience` into web result, PDF, and email; `_innovation_context`
  now resolves the whole band and returns `tagline`/`description`, returning `None` if the band
  is absent. `pdf_utils.py`/`email_utils.py` gained `audience=None` params threaded into both
  email bodies and the attached PDF. Audience now reaches all three surfaces — this closes the
  real gap the spec flagged (PDF/email previously had no audience param).

**Check 1 — Laggard tagline.** `content/survey.yaml:376` is byte-for-byte
`tagline: "You are a Laggard. Wanker."` — single occurrence, not softened anywhere. Tester
also confirmed it renders verbatim on web, PDF, and both email bodies via a real low-score
submission.

**Check 2 — relationships stay out of email.** `_persona_card.html` (web+PDF only) carries the
renamed `Natural allies:`/`Friends:`/`Necessities:` blocks. Email templates only swapped the
description line and extended the band block — no relationship markup added. This matches the
pre-existing scope boundary; not a regression (email never had brethren/besties/battlers).
Guarded by `test_email_bodies_never_render_persona_relationships`.

**Check 3 — optional validation + macro fallback.** Confirmed above. `description` stays
required; `description_organisation` optional; the 3 small fixtures (no such field) are
unaffected — full suite green proves it.

**Check 4 — CSP/security.** Templates touched (`_persona_card`, `_result_innovation`, both
email bodies, `_macros`) add zero `<script>` tags, no Alpine, no `unsafe-eval`. The only
scripts in the app remain the pre-existing nonce'd `step.html` block and the CSP-allowlisted
Bootstrap CDN. No inline-script regression.

**Check 5 — tester scope.** Tester commit `2dac2e6` touched exactly one file,
`tests/test_persona_copy_verification.py` (+314 lines, 12 tests). No production code modified —
diff confirms the claim.

**Tests are meaningful.** The org/individual e2e tests assert both the presence of the correct
wording AND the absence of the wrong wording (`'Your organisation sees...' in body` and
`'You see...' not in body`), which is the exact guard the spec demanded against a
silently-falling-back macro masking a missing-audience bug. Tester's additions add real value
(2-value relationship rendering, Laggard via a genuine low-score submission, un-routed
`audience is None`, missing-org-field fallback, and the loader band-field failure cases the
coder's parametrize list had missed). I re-ran the suite independently: **265 passed**.

## Doc check (gitignored CLAUDE.md / backlog/CONTEXT.md — read off disk)

The orchestrator's manual fix to `CLAUDE.md` is accurate and thorough. Lines 29-36 and 219-253
correctly describe: the audience-aware `description`/`description_organisation`, the
`brethren`/`besties`/`battlers` → `natural_allies`/`friends`/`necessity` reframe (correctly
called a genuine semantic reframe, not a synonym swap), the band tagline/description, the
`persona_description()` macro, the Laggard swear-word exception, and the email-parity boundary
(relationships stay web+PDF only). `backlog/CONTEXT.md` is about the backlog directory itself
and needs no #0004 changes. No stale `brethren`/`besties`/`battlers` references-as-current and
no "8 of 9 placeholder" language survive in the narrative.

**Minor nit (non-blocking):** `CLAUDE.md:74`, the file-tree comment on `content/survey.yaml`,
still reads `# real 11-question survey content, placeholder persona copy`. Post-#0004 the
persona tagline/description copy is now real (only `case_studies`/`resources` remain Phase-2
placeholders). This one-line comment now contradicts the doc's own narrative sections. Worth a
quick edit to e.g. "real survey + persona copy; case_studies/resources still placeholder" — but
it's a gitignored local doc and does not affect shipping code, hence SHIP not NEEDS WORK.

## How to verify and merge

Base branch is **`dev`** (this repo uses a strict main=production / dev=active-development split).
Do NOT merge into `main` — that is a separate, deliberate release step (Phase 6 auto-deploys
from `main`) and is out of scope for this pipeline.

**Verify** (from `/Users/tomspice/Projects/monkey-puzzle`):
```
source .venv/bin/activate
python -m pytest tests/ -q          # expect 265 passed
```
No DB migration in this change (content-only YAML + display threading; spec explicitly forbade
a migration and none was added), so no Alembic step is required.

Manual checks the green suite does not fully cover (worth a 2-minute eyeball since the copy is
client-facing and public-repo):
- Run the app and complete the survey on BOTH tracks, then open the result page, download the
  PDF, and (if `MAIL_SERVER` is configured) email yourself:
  - organisation track shows the "Your organisation ..." description wording;
  - individual track shows the "You ..." wording.
- Confirm the Laggard band renders "You are a Laggard. Wanker." verbatim (reach it with a
  low innovation score) — deliberate, do not soften.
- Optionally apply the CLAUDE.md:74 comment tidy above before merging.

**Merge** (nothing is pushed unless you run `git push`):
```
git checkout dev
git merge --no-ff feature/persona-and-innovation-curve-copy
git branch -d feature/persona-and-innovation-curve-copy   # optional
git push origin dev                                        # when ready
```
Per your saved workflow, do not re-run tests on merge into `dev` — the pipeline already tested
this branch.

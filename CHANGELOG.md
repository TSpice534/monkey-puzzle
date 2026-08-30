# Changelog

All notable changes are documented here. Add a bullet to `Unreleased` after every completed task on `dev`. On release, rename this section to `[v<version>] — YYYY-MM-DD` and add a fresh `Unreleased` block at the top.

---

## Unreleased

- Feature: colour-code Natural Allies / Friends / Necessities on the result-page persona
  grid (backlog #0031) — each of the 8 non-selected cells whose persona is one of the
  classified persona's `natural_allies`/`friends`/`necessity` now gets a `grid-cell--ally`/
  `--friend`/`--necessity` modifier (blue/teal/purple, new `--rel-*`/`--rel-*-tint` vars in
  `theme.css`), with a hard-stop diagonal-gradient split when one persona falls into more
  than one category (e.g. Inventor's Architect cell, which is both ally and necessity). A
  new `<ul class="grid-legend">` key renders below the grid, one entry per non-empty
  category, plus a "A cell showing two colours is both." note when two or more categories
  are populated. Each coloured cell also gets a screen-reader-only label (`Natural ally`,
  `Friend`, `Necessity`) so the relationship isn't colour-only. The selected cell keeps
  `grid-cell--selected` and never also gets a relationship class. No Python/route changes —
  `_result_grid.html` already had `persona` in its render context.
- Feature: certificate-style share image + personalised LinkedIn caption (backlog #0030) —
  a new `GET /survey/<token>/certificate.png` route rasterises a square 1200x1200 "Download
  certificate" PNG (`app/survey/charts.py::render_certificate_svg`, framed in the
  innovation-curve band's accent colour when the submission has one, else `--brand-primary`,
  band named as text never colour alone, with a `tomspice.co.uk/monkey-puzzle` footer line
  near the bottom of the frame so a downloaded/reshared certificate keeps its CTA even once
  it's separated from the caption), reusing the existing on-disk asset cache
  (`get_or_render`) so it self-invalidates on a `content/survey.yaml` retune exactly like
  `share.png`/the PDF. The result page's "Share or save your result" card gains a "Download
  certificate" link plus, when the survey defines a new optional top-level `share_caption`
  yaml key (`template`, `{persona}`/`{url}` placeholders — resolved by a new
  `_caption_context` helper, home-page URL not the token result URL), a read-only textarea
  with the personalised caption text and a progressive-enhancement "Copy caption" button
  (rendered `hidden`, unhidden by a small nonce'd vanilla script — the copy-to-clipboard
  falls back to a "Press Ctrl/Cmd+C" hint when `navigator.clipboard` is unavailable). No new
  `Submission` column/migration — the caption is derived at render time, same as
  `_why_context`/`_now_next_context`.
- Change: corrected 4 persona necessity relationships (Inventor, Communicator, Connector,
  Cooperator) in `content/survey.yaml` and `docs/PROFILES-TEMPLATE.md` to match Tom's
  resolved relationship table (backlog #0027).
- Change: renamed the "Where you sit on the innovation curve" heading to "Your focus
  group on the innovation curve" on the result page and in the result email (HTML +
  plain text) for consistency (backlog #0026).
- Fix: innovation-curve band labels no longer overlap, and add the app's first responsive
  breakpoint (backlog #0029) — `app/survey/charts.py::render_innovation_curve_svg` now runs
  a collision-aware label layout pass (`_layout_band_labels`/`_estimate_text_width`, with a
  font-size shrink-to-fit fallback) instead of blind span-centering; a new
  `@media (max-width: 767.98px)` block in `theme.css` stacks the spectrum question options
  (Q2/Q3/Q4) vertically, shrinks the triangle widget, and tightens the result-page 3x3 grid,
  plus a new `.innovation-curve svg { max-width: 100%; height: auto; }` rule so the chart
  scales inside a narrow card; `_result_grid.html`'s table gained a `.table-responsive`
  wrapper as a backstop.
- Fix: post-#0029 manual mobile QA turned up two real follow-up bugs the pipeline's review
  missed. (1) `theme.css`'s mobile breakpoint comment read "...matching the col-sm-*/col-md-*
  classes..." — the literal `*/` mid-sentence closed the comment early, so every real CSS
  parser (WebKit, Gecko) silently discarded the entire `@media` block from that point on,
  even though the raw file text looked completely intact; fixed the comment wording and added
  `test_theme_css_has_no_premature_comment_close` (`tests/test_mobile_responsive_layout.py`)
  to catch this class of bug going forward. (2) `.triangle-node` had a `min-width` but no
  `max-width`, so a long option label rendered unwrapped and its corner-anchored overhang
  (half the node's width always sits outside the triangle by design) pushed well past the
  viewport at 320-375px; capped the node's width and shrank the widget/font size to keep the
  overhang inside the page margin. Also added an mtime-based cache-busting query string to
  `theme.css`'s `<link>` tag (`app/__init__.py`, `base.html`) as a general hardening measure
  encountered while debugging this.
- Change: replaced the persona card's bare `Natural allies:`/`Friends:`/`Necessities:` label
  lines with full sentence copy ("You probably work closely with an **Accountant**.", etc.,
  role names bolded) under "Natural Allies"/"Friends"/"Necessities" subheadings on the web
  result page and PDF (backlog #0028). New `role_phrase()` macro in `_macros.html` handles
  the singular article rule ("an Accountant") and the pair/multi Oxford-comma join (persona
  names verbatim, "The" prefix included — e.g. "The Implementer and The Cooperator"),
  bolding each name via static `<strong>` markup around the per-name `{{ }}` output
  (auto-escaping stays intact, no `| safe`). Added a divider (`<hr>`) between "Now and
  next" and this section for visual separation, shown only when both sides have content.

## [v0.3.2] — 2026-08-07

- Change: remove the radar (fingerprint) chart from the remaining result surfaces — PDF
  download, emailed PDF copy, and the share-card PNG (backlog #0025, closing the gap #0020
  left). Deletes the now-unused `render_fingerprint_svg` generator from `app/survey/charts.py`;
  the share card is relaid out to fill the freed space with the persona name/tagline block.

## [v0.3.1] — 2026-08-07

- Change: add an instruction line and visual separator to the combined profile step (Question
  7) (backlog #0024) — new optional `profile_matrix.instructions` field in `content/survey.yaml`
  ("Select one option from the top AND bottom row"), validated in `loader.py` and rendered in
  `_question_profile_pair.html` above the live sentence, plus an `<hr>` divider between the
  approach and scope option rows.
- Change: remove the radial (fingerprint) chart from the web results page (backlog #0020) —
  dropped from `app/templates/survey/result.html` and `routes.py::result()`. PDF, emailed
  copy, and the share-card PNG each render it independently and are unaffected.
- Fix: split test-only deps out of the production requirements lock (backlog #0023) —
  `pytest` moved from `requirements.in` into a new `requirements-dev.in`/`requirements-dev.txt`
  (pip-tools layered lock, `-c requirements.txt`), so `pytest`, `iniconfig`, and `pluggy` no
  longer install on the production server via `DEPLOY.md`'s `pip install -r requirements.txt`.
  Local dev/CI now installs both files.
- Change: cache the share-card PNG and result PDF on disk (backlog #0022) — `share_image`
  and `download_pdf` now rasterise each distinct asset once (content-addressed cache under
  `ASSET_CACHE_DIR`) and serve repeats from disk, so social-crawler `og:image` fetches and
  PDF re-downloads no longer tie up the 3 sync Gunicorn workers. Self-invalidates when
  `content/survey.yaml` is retuned.
- Fix: cap free-text answer length and rate-limit /start and /step (backlog #0021) — `short_text`
  answers are truncated to `MAX_SHORT_TEXT_CHARS` (2000) in `_read_answer` and the textarea in
  `_question_short_text.html` gains a matching `maxlength`; `/start` and `/<token>/step` gain
  per-IP `@limiter.limit` decorators (mirroring `/<token>/email`), closing a storage-exhaustion
  DoS on the unauthenticated survey routes.

## [v0.3.0] — 2026-08-04

- Change: reword and move the "why" question, surface it on results (backlog #0015) —
  `why_reason` (`content/survey.yaml`) is reworded from "Do you have a \"why\"? A reason
  why this topic is relevant or important for you?" to "In one sentence, why is this work
  on this topic important to you?", moves from question 2 to the last question in the
  survey (after `target_groups`), and gains a new `output: why` tag (added to
  `app/survey/loader.py`'s `_VALID_OUTPUTS`). The respondent's own free-text answer now
  renders on the web result page and in the PDF report, via a new `_why_context` builder in
  `app/survey/routes.py` (mirroring `_now_next_context`), threaded through
  `generate_result_pdf`'s new `why` kwarg, and a new shared partial
  `app/templates/survey/_result_why.html` included in `_persona_card.html` just below the
  persona description. Skipped/blank answers and submissions predating the question render
  nothing — no crash, no guard needed on the step route
- Change: replace landing page lead copy with survey description text (backlog #0016) —
  `app/templates/index.html`'s `<p class="lead">` now describes what the survey captures
  and that results are personalised and shareable, replacing the prior "what it is / how
  many questions" blurb.
- Change: rename the Developer and Advocate personas to Inventor and Architect (backlog
  #0018) — a full id-level rename (`developer`→`inventor`, `advocate`→`architect`) across
  `content/survey.yaml` (persona blocks, relation lists, grid cells, tie-break order,
  innovation-curve persona modifiers), the two persona icon SVGs under
  `app/static/icons/` (renamed, no content change), all test fixtures and test files that
  mirror the real persona set, and the persona-name lists in `README.md`,
  `docs/INNOVATION-SCORING-TEMPLATE.md`, `docs/PRODUCTION-PLAN.md`, and
  `docs/PROFILES-TEMPLATE.md` (also fixes that doc's stale relationship-column references
  to the old names). Taglines, descriptions, grid positions, and tie-break/modifier values
  are unchanged — a pure token rename.
- Change: reword four question prompts/options and add per-question help text (backlog
  #0017 Part A) — `content/survey.yaml`'s `space_to_progress` prompt and all 5 option
  labels move to audience-neutral wording (drops `label_organisation` on that question),
  `support_type`'s prompt changes to "What type of assistance do you desire?", and
  `target_groups`'s prompt changes to "Who are you trying to work with?" (options
  unchanged on both). Also adds a new optional per-question `explanation` string field —
  distinct from `instructions` — validated generically in `app/survey/loader.py` for every
  question type, and rendered once, auto-escaped, below the prompt in
  `app/templates/survey/step.html` (`.question-explanation`, `white-space: pre-line` in
  `app/static/css/theme.css`, so multi-line explanations stored as YAML block scalars
  render with visible line breaks). `space_to_progress`, `need_most`, `have_enough`, and
  `support_type` all gain explanation text; `target_groups` has none, matching the source
  template.
- Change: replaced the interactive 3x3 profile grid input with two single-select
  questions (`profile_approach` / `profile_scope`) resolving the same 9 personas via a
  new `profile_matrix` construct; removed `type: grid` schema support; the labelled 3x3
  grid still renders on the result page, now driven by the two answers (backlog #0017
  Part B).
- Change: merged the two profile questions (`profile_approach` / `profile_scope`) onto a
  single survey page with a shared prompt, a live-updating sentence, and a 2x3 button
  grid; both selections remain mandatory and resolve the same persona via
  `profile_matrix` (backlog #0017 Part B follow-up). A new `survey_steps()` helper in
  `app/survey/loader.py` groups the two adjacent profile questions into one rendered
  step (every other question keeps its own step); `profile_matrix` gains `prompt`/
  `sentence_stem` fields and an adjacency validation check; persona resolution and the
  result-page grid are unchanged. The real survey drops from 12 steps back to 11.
- Change: add org-register prompt support and fix the profile step's aria-label register
  (backlog #0019) — a new optional per-question `prompt_organisation` string field
  (loader-validated, same shape as `label_organisation`), rendered via a new
  `question_prompt(question, audience)` macro in `app/templates/survey/_macros.html`.
  `content/survey.yaml`'s `profile_approach` question is the only one that gains a
  `prompt_organisation` ("Complete the following sentence: \"We want to...\""), matching
  `docs/SURVEY-TEMPLATE.md` — no other question has a distinct org-register prompt.
  `profile_matrix` gains a matching optional `sentence_stem_organisation` ("We want to"),
  resolved in `app/survey/routes.py::_render_step` so the combined profile step's live
  sentence flips register on the org track. `_question_profile_pair.html`'s two
  `role="radiogroup"` `aria-label`s, which previously used `question.prompt` directly and
  so stayed individual-register even on the org track, now go through `question_prompt`
  too, alongside `step.html`'s single-question legend.

## [v0.2.0] — 2026-07-24

- Feature: topics question (Q9) — choose up to 3, not exactly 3 (backlog #0014) —
  `topics` changes from `type: multi_exact` (`choose_exactly: 3`) to a new
  `type: multi_range` (`choose_min: 1`, `choose_max: 3`), so respondents can select
  between 1 and 3 topics instead of exactly 3. Reworded the prompt (drops "three") and
  added a data-driven optional `instructions` string field ("Choose up to 3 options."),
  rendered above the option cards in `_question_multi.html` (mirroring `grid`'s
  instruction-line pattern). `multi_range` behaves like `multi`/`multi_exact` everywhere
  a list-of-indices answer is consumed — loader validation, the route's block-advance
  guard (flash: "Please select between {min} and {max} options."), scoring, and the
  Now/Next narrative. `multi_exact` and its `choose_exactly` field are unchanged
- Feature: spectrum box-row selector (backlog #0013) — the `type: spectrum` widget
  (`motivation`/`ambition`/`space_to_progress`) is now a horizontal row of clickable
  boxes instead of a native `<input type=range>` slider: one full box per labelled
  option, plus a small "mix" dot per `unlabelled` between-option (e.g. `motivation`'s
  indices 1 and 3), positioned between its two labelled neighbours — mirroring the
  triangle widget's corner/edge-node pattern (native radios + `:checked`-sibling CSS,
  no JS). `_question_spectrum.html` is a full rewrite; the mix box's visible text is
  empty, with a `visually-hidden` span naming both flanking options for screen readers.
  `theme.css`'s `.spectrum-widget .form-range` rule is replaced with
  `.spectrum-node`/`.spectrum-node--mix` styles cribbed from `.option-card` and
  `.triangle-node`/`--edge`. `step.html`'s `{% block scripts %}` override (the live-label
  JS that drove the old slider) is removed entirely — this was the last inline script on
  the step page. No backend, scoring, data-model, or `content/survey.yaml` change: a
  spectrum answer is still a single option index, same as `single`

## [v0.1.3] — 2026-07-20

- Fix: innovation-curve score cap (backlog #0012) — the Innovators band is a single point
  (15), but `resolve_innovation_curve` returned the raw uncapped total (the persona
  modifier could push it as high as 19), and `content/survey.yaml`'s Innovators band
  ceiling was still `max: 20`, so the bell-curve chart (backlog #0011) rendered 21 bars
  past the true top score. `Innovators.max` in `content/survey.yaml` is now `15` (from
  `20`), and `resolve_innovation_curve` clamps the returned `score` to
  `min(total, ceiling)`, where `ceiling = max(b['max'] for b in bands)` — never
  hardcoded, so a future template retune needs only the yaml edit. Band resolution still
  runs against the raw uncapped total, unchanged (its existing out-of-range fallback
  already resolves any total >= 15 to Innovators). `app/survey/charts.py::render_innovation_curve_svg`
  derives its bar range from the same bands config, so it now renders 16 bars (0-15) and
  reads "of 15" automatically — no chart code change needed
- Feature: innovation-curve visualisation on the results page (backlog #0011) — the
  innovation-curve card now includes an inline-SVG bell-curve chart alongside the
  existing band text, styled on the fingerprint radar's hand-built SVG pattern (no JS,
  no external assets, CSP- and WeasyPrint-safe). `app/survey/charts.py::render_innovation_curve_svg`
  draws 21 equal-width bars (one per score point, 0–20) with heights following a
  symmetric Gaussian envelope so the silhouette reads as a bell curve, Innovators
  leftmost through Laggards rightmost (matching Rogers' classic diffusion diagram), the
  respondent's exact score highlighted at full colour and full opacity — every other bar
  keeps the same bold band colour but renders at reduced `fill-opacity`
  (`UNHIGHLIGHTED_BAR_OPACITY`) rather than being desaturated. Five band names render as
  section labels along the bottom; the `aria-label` always names the score and band,
  never colour alone. `_innovation_context` (`app/survey/routes.py`) threads the
  pre-rendered `curve_svg` onto the existing `innovation` context dict, so it reaches the
  web result page and PDF via the shared `_result_innovation.html` partial (inserted
  under the `<h2>`, above the existing swatch/name text) — email is unaffected, matching
  #0002's established web+PDF-only precedent for that partial. `tests/test_sharing.py`
  (+6) covers bar count, highlight opacity, the `None`-score and empty-bands edge cases,
  and the band-name labels — 375 tests total
- Feature: edge points on triangle questions (backlog #0010) — the 3 `type: triangle`
  questions (`need_most`, `have_enough`, `support_type`) gain 3 tappable edge midpoint
  nodes alongside the existing 3 corners, so a respondent can pick a point *between* two
  corners. An edge pick is positional (no new authored options) and encodes as an
  `"i,j"` ascending-index pair submitted from the form, exactly like the `grid` widget's
  `"x,y"` cells (`app/survey/routes.py::_read_answer`, new `triangle` branch). In the
  Now/Next results copy, an edge pick resolves to both flanking corners'
  `statement_phrase`s joined with "and" (e.g. "capacity and knowledge") via the existing
  list-join branch in `app/survey/persona.py::resolve_now_next`, widened to also match a
  list-typed triangle answer. `_question_triangle.html` renders the 3 edge nodes with a
  smaller `.triangle-node--edge` CSS sizing modifier so all 6 nodes fit the triangle
  widget without overlapping
- Tests: `tests/test_persona.py` (+2 for edge-pick `resolve_now_next` resolution on
  `have_enough`/`need_most`), `tests/test_real_survey_e2e.py` (+2 for edge-node
  rendering and the edge-pick POST/persist round-trip on the real survey),
  `tests/test_grid_flow.py` (+1 for `_read_answer`'s triangle branch parsing both a
  corner index and an edge pair) — 343 tests total

## [v0.1.2] — 2026-07-16

- Fix: production 500 ("no such table: submission") on every survey start, despite
  `flask db upgrade` reporting success — Flask-SQLAlchemy 3.x resolves a *relative*
  `sqlite:///` URL against `app.instance_path`, not the process's CWD. `.flaskenv`'s
  `DATABASE_URL=sqlite:///monkeypuzzle.db` meant CLI commands (`flask db upgrade`,
  loaded via `.flaskenv`) silently migrated `instance/monkeypuzzle.db`, while Gunicorn
  (which never loads `.flaskenv`, and has no `DATABASE_URL` in its `.env`) fell back to
  `config.py`'s absolute default and ran against a completely different, un-migrated
  `monkeypuzzle.db` at the repo root. Removed the relative override from `.flaskenv`
  entirely so every context (local dev, CLI, Gunicorn) resolves the same absolute path
  from `config.py`. `tests/test_database_url_config.py` (new, 2 tests) guards against
  reintroducing a relative `DATABASE_URL` in `.flaskenv` and asserts `config.py`'s
  no-env-var-set fallback stays absolute

## [v0.1.1] — 2026-07-16

- Fix: subpath deploy 404'd on every route — Nginx's `proxy_pass` (no URI component)
  forwards the full request path unchanged, including the `/monkey-puzzle` prefix, but
  `ProxyFix(x_prefix=1)` only sets `SCRIPT_NAME` from `X-Forwarded-Prefix`, it never
  strips the prefix back off `PATH_INFO` — so the app's route table (registered without
  any prefix) never matched. Added a small WSGI middleware
  (`app/__init__.py::_strip_script_name`) that strips `SCRIPT_NAME` off the front of
  `PATH_INFO` once `ProxyFix` has set it, applied as the innermost wrapper so it sees the
  value `ProxyFix` derived from the header. Local dev / domain-root requests (no
  `X-Forwarded-Prefix` header) are unaffected. `tests/test_subpath_deployment.py` (new,
  4 tests) covers the plain-request no-op case, the previously-404ing root and nested
  routes under a simulated `/monkey-puzzle` prefix, and that `url_for()`-generated links
  still carry the prefix

## [v0.1.0] — 2026-07-16

- Feature: deploy workflow, script, and guide (backlog #0006) — `deploy/monkeypuzzle.service`
  (systemd unit) and `deploy/nginx-monkeypuzzle.conf` (the two `location` blocks to
  hand-merge into the live multi-tenant Nginx config), a root-level `deploy.sh.example`
  (mirrors the Donut Toolkit's untracked-`deploy.sh` pattern), and a new `DEPLOY.md`
  step-by-step guide, all cloning the Donut Toolkit's proven Infomaniak VPS pattern for a
  new `monkeypuzzle` systemd service on the **same** box, served at the subpath
  `tomspice.co.uk/monkey-puzzle` (existing TLS cert reused, no DNS/Certbot step). Files
  and guide only — no VPS command was run and the GitHub repo was not created/pushed;
  both remain manual steps for Tom
- Fix: spectrum slider's live label rendered apostrophes/entities as the literal escaped text (e.g. `&#39;`) instead of the character — `_question_spectrum.html`'s `ns.labels` was built from the `option_label(...)` macro's already-HTML-escaped `Markup` output, then double-encoded again through `tojson` into the `data-labels` attribute and read back verbatim via `JSON.parse` + `textContent` in `step.html`'s JS (backlog #0008). `ns.labels` is now built from the raw `label`/`label_organisation` string (inlining the macro's own conditional) so `tojson` only escapes once, correctly. Also removed the static row of all option labels below the slider, now that the live label is the sole (and correctly-rendered) label — the widget's no-JS fallback comment updated accordingly: the native range input still submits a valid index and the current label still renders server-side, but the other option labels are no longer shown while dragging (backlog #0009)
- Feature: real persona tagline/description copy (now audience-aware) and Natural Allies/Friends/Necessities relationships; innovation-curve band taglines + descriptions across web/PDF/email (backlog #0004) — all 9 personas in `content/survey.yaml` get their final `tagline`/`description` copy from `docs/PROFILES-TEMPLATE.md`, plus a new optional `description_organisation` field (mirroring the existing `label`/`label_organisation` option pattern) resolved at render time by a new `persona_description(persona, audience)` macro; `brethren`/`besties`/`battlers` are renamed to `natural_allies`/`friends`/`necessity` (a genuine reframe, not just a rename — "battlers"/"likely friction" becomes "Necessities:", read as complementary needs) with matching label changes on the persona card. All 5 `innovation_curve.bands` gain `tagline`/`description` copy from `docs/INNOVATION-TEMPLATE.md` (now required, validated in the loader), shown on the innovation-curve card on all three result surfaces — including the Laggard tagline kept verbatim as given. `submission.audience` is now threaded through `app/pdf_utils.py::generate_result_pdf` and `app/email_utils.py::send_result_email`/`_send_async` (neither previously received it) so the organisation-track description resolves correctly on the PDF and in both email bodies, not just the web result page. Persona relationships stay web+PDF only — not added to email, a pre-existing gap, not a regression
- Tests: `tests/test_loader.py` (renamed relationship-field tests to `natural_allies`, +4 for `description_organisation` validation/fallback), `tests/test_real_survey_e2e.py` (repointed the inline persona-dict field names, +2 asserting the web result page shows organisation-wording vs individual-wording persona descriptions on the correct track) — 253 tests total
- Feature: Rogers' innovation-curve scoring + Documenter→Accountant rename (backlog #0002) — the `motivation`/`ambition`/`space_to_progress` questions now carry per-option `score` (motivation gained its 2 missing unlabelled between-stops via a new `unlabelled: true` option field; ambition/space_to_progress each gained their missing 5th middle option, per `docs/SURVEY-TEMPLATE.md`), aggregated by a new `app/survey/persona.py::resolve_innovation_curve` against a new top-level `innovation_curve:` construct (persona modifiers + Rogers-curve bands + hex colours, all data-driven in `content/survey.yaml`, none hardcoded). The result (band + score) is stored on two new `Submission` columns (`innovation_band`/`innovation_score`, via a new Alembic migration) and shown as a card on **all three** result surfaces — web (directly below "Your position on the grid"), PDF, and email (HTML + plain text) — via a new shared `_result_innovation.html` partial for web/PDF and inline markup for the two email bodies, mirroring how email already inlines persona info. Also renamed the "Documenter" persona to "Accountant" throughout (bundled per Tom), including reworked accountant-framed tagline/description copy and every cross-reference (other personas' `brethren`/`besties`/`battlers`, the grid cell, `scoring.tie_break`)
- Tests: `tests/test_loader.py` (+16 for option `score`/`unlabelled` and the `innovation_curve` construct), `tests/test_persona.py` (+6 for `resolve_innovation_curve`, incl. the two worked examples against the real survey and the no-`innovation_curve`/unknown-persona/missing-answer defensive paths), `tests/test_real_survey_e2e.py` (+10 — full-flow innovation-curve persistence for both audience tracks, a high-scoring Innovators worked example, the band card's position on the result page, the PDF/email templates rendering the band name, and the 5-position `motivation` slider incl. the unlabelled stops never rendering their placeholder text), and `tests/test_innovation_curve_verification.py` (new, 10 tests — independent re-verification of the band card's position, the PDF colour accent at the WeasyPrint content-stream byte level, actual dispatched email content via `mail.record_messages()`, and a malformed-answer defensive case) — 247 tests total. All `documenter`/`Documenter` references across fixtures and tests repointed to `accountant`/`Accountant`
- Docs: added `CLAUDE.md`, `CONTEXT.md`, and `backlog/CONTEXT.md` (gitignored, local-only), plus `CHANGELOG.md` and `VERSION` (tracked), replicating the Donut Toolkit's project-navigation doc system for this repo
- Feature: Phase 1 skeleton — Flask app factory with CSP nonce + full security-header set (ported from Donut Toolkit, stripped of auth/admin/mail/limiter/client-config), `main`/`errors` blueprints, base templates, anonymous `Submission` model (token, answers JSON, persona_id, score_vector, timestamps) + first Alembic migration. Pytest suite (24 tests) covering security headers, error pages, model persistence, and the prod dev-secret boot guard
- Feature: Phase 2 data engine — `content/survey.yaml` loader + schema validation (`app/survey/loader.py`), a realistic placeholder `survey.yaml` (13 questions across Rob's seven axes, all nine personas with stub allies/case-studies/resources), and `SURVEY_PATH` config
- Feature: Phase 3 survey flow — data-driven `survey.start`/`survey.step`/`survey.result` routes persisting answers to `Submission.answers` by question id (zero-based option indices); single/multi/spectrum/short_text widgets built from native HTML + CSS (`:checked` sibling styling) instead of Alpine.js, with one small nonce'd vanilla script for the spectrum slider's live label — resolves the Phase 1 Alpine/CSP conflict without weakening the CSP
- Feature: Phase 4 persona classifier + result page — `app/survey/persona.py` (score/apply_modifiers/classify, deterministic tie-break) and `app/survey/charts.py` (`render_fingerprint_svg`, an inline-SVG radar over the nine personas' `score_vector`), plus the result page (persona card + radar chart)
- Tests: `tests/test_loader.py`, `tests/test_persona.py`, `tests/test_survey_routes.py` (60 new tests, 84 total) covering schema validation, the data-driven weight-swap contract, deterministic persona classification for all nine personas, and the full survey flow including edge cases (unknown token, out-of-range step, result-before-completion, security headers)
- Fix: Phase 4's `render_fingerprint_svg` rim labels (e.g. "Entrepreneur") could clip against the SVG's own canvas edge — the chart now pads its canvas beyond the logical chart `size` so labels always have margin, whether embedded standalone or nested in another SVG
- Feature: Phase 5 share/output — OpenGraph/Twitter meta tags and a generated 1200x630 PNG share image (`app/survey/charts.py::render_share_card_svg`, rasterised via cairosvg) on the result page for rich LinkedIn/Twitter previews; a LinkedIn share-intent link; a downloadable PDF report (`app/pdf_utils.py`, WeasyPrint, reusing the persona card partial and fingerprint chart); and an opt-in "email me a copy" (`app/email_utils.py`, Flask-Mail, sent in a background thread, PDF attached) — the email address is never persisted, matching the anonymous/no-accounts design. The email route is rate-limited (Flask-Limiter, 5/hour) since it's the one endpoint that can send outbound mail on an anonymous request
- Tests: `tests/test_sharing.py` (19 new tests, 111 total) covering the share image, PDF download, and email routes (validation, config-gate, rate limiting, dispatch), the background send pipeline (PDF attachment + failure fallback), the share-card SVG renderer, and a regression test for a Jinja block-scoping bug that briefly made the LinkedIn share link/OG tags point at an empty URL
- Feature: respondent-type routing — the survey's first question now asks "individual or organisation?" and the answer (`Submission.audience`, new nullable column + migration) determines which of the rest of the questions show. `content/survey.yaml` gains a `respondent_type_question` key naming the router, and any question can be tagged `audience: [individual]` / `[organisation]` to restrict it to one track (untagged questions stay shared). The engine change is generic (`app/survey/loader.py::effective_questions`) — `respondent_type_question` is optional, so existing/fixture surveys without a router keep working unchanged. Placeholder content: `team_appetite`/`pace_preference` (organisation-only, unchanged wording) now have first-person `personal_appetite`/`personal_pace` counterparts (individual-only) so both tracks have comparable depth (14 steps each)
- Tests: `tests/test_loader.py` (+16), `tests/test_audience_routing.py` (28 new tests, 139 total) covering router-question schema validation, `effective_questions()` filtering, and the full organisation/individual flows end-to-end (incl. switching tracks mid-survey and unequal step counts) against a dedicated fixture (`tests/fixtures/survey_audience.yaml`)
- Feature: real survey content, output routing, interactive persona grid (backlog #0003, merges #0001) — `content/survey.yaml`'s placeholder `questions:` replaced with the real 11-step survey from `docs/SURVEY-TEMPLATE.md`; three new question types (`triangle` — a bespoke CSS-drawn triangle selector with three corner options, native `:checked`-sibling styling, no Alpine/no `unsafe-eval`; `multi_exact` — a fixed-count multi-select; `grid` — the interactive 3x3 persona-profile grid); a new `output` schema tag (`innovation_curve`/`now`/`next`/`profile_direct`, validated only — display/aggregation is backlog #0002); per-option audience wording via an optional `label_organisation` field, resolved at render time by a new `option_label()` macro; and a new top-level `profile_question` key naming the grid, which now **directly** resolves the winning persona (`app/survey/persona.py::resolve_profile_persona`) instead of weighted classification — the grid is **mandatory to advance** (same block-advance mechanism as `multi_exact`'s wrong-count guard), so `classify_submission`'s tie-break fallback is now defensive-only (kept for direct-DB-edited/partial submissions). The result page additively renders a labelled, highlighted 3x3 grid (`_result_grid.html`) alongside the existing radar/fingerprint chart, which is unchanged. `dimension` and `weights` are now optional on questions/options (nothing currently consumes `dimension`; a missing `weights` contributes zero, same as before)
- Tests: `tests/test_loader.py` (+23 for the new types/`output`/`label_organisation`/`profile_question`), `tests/test_persona.py` (repointed weighted-scoring tests to `tests/fixtures/survey_min.yaml` since the real survey's weighted placeholder questions are gone; replaced the single dominant-question test with a grid-direct test parametrized over all 9 cells, plus defensive-fallback and grid-wins-over-weighted-answers tests, +8), `tests/test_grid_flow.py` (new, 14 tests — grid persistence/mandatory-advance, `multi_exact` exact-count enforcement, `triangle` persistence/rendering, per-audience wording, the result-page grid, security headers) against a new fixture `tests/fixtures/survey_grid.yaml`, and `tests/test_real_survey_e2e.py` (new, 20 tests — closes the gap that no test previously drove the actual production `content/survey.yaml` through the Flask routes: full 11-step happy path for both audience tracks, all 9 grid-cell mappings, and the radar/PDF/share/email routes against the new content shape) — 204 tests total
- Fix: the result-page labelled persona grid (`_result_grid.html`) rendered as a single stacked column instead of a 3x3 table — `.grid-cell` (`display: flex`) was applied directly to the `<td>`, which overrides the browser's default `table-cell` display and breaks the table out of normal row/column layout. Moved the class to a nested `<div>` inside the `<td>` (matching the pattern the question-time grid already used correctly). Added a regression test (`tests/test_real_survey_e2e.py`) asserting the `<td>` never carries `grid-cell` directly — 205 tests total
- Fix: the result-grid's selected-cell highlight (border color + slightly darker text) was too low-contrast against the muted cells to read as "the answer" at a glance. `.grid-cell--selected` now gets a solid brand-green fill, white bold text, a checkmark, and a drop shadow; `.grid-cell--muted` pushed further back with reduced opacity
- Feature: vector icons for persona cards and result grid (backlog #0005) — each of the 9 personas gets a placeholder line-art SVG (`app/static/icons/<id>.svg`, sourced from Bootstrap Icons 1.11.3), inlined into templates via a new Jinja global `persona_icon()` (`app/survey/icons.py`, reads the file off disk once and caches it, same inline-SVG approach as the fingerprint radar chart) rather than `<img>`/`url_for('static', ...)` — inline `<svg>` needs no CSP `img-src` grant and avoids an HTTP round-trip inside WeasyPrint's PDF render. `content/survey.yaml` gained a static-relative `icon:` field per persona (validated as an optional non-empty string in `loader.py`, mirroring `label_organisation`). The icon renders next to the persona name on the persona card (`_persona_card.html`, shared by web + PDF) and above the name in each labelled result-grid cell (`_result_grid.html`, web only), styled by new `.persona-icon`/`--card`/`--grid` rules in `theme.css` (and duplicated into `pdf/result.html`'s own inline `<style>`, since the PDF doesn't load `theme.css`). Grid icons inherit `currentColor` so they read white/muted-grey matching the selected/muted cell text. Scope intentionally excludes the question-time grid and email templates (out of scope per the backlog item)
- Feature: "Now" / "Next" narrative result statements (backlog #0007) — the two `output: now` / `output: next` question sets (`topics`/`have_enough` and `need_most`/`support_type`/`target_groups`) are now assembled into a pair of sentences via a new `app/survey/persona.py::resolve_now_next`, using a new top-level `now_next:` construct in `content/survey.yaml` (two `{placeholder}`-templated sentences, plus optional `now_organisation`/`next_organisation` overrides — not supplied yet, see below) and new per-option `statement_phrase`/`statement_phrase_organisation` fields on the affected options (so e.g. "More capacity" reads as "…looking for more capacity", and the 3 selected `topics` join with an Oxford comma). Deliberately **derived at render time** in `app/survey/routes.py::_now_next_context`, not persisted — no new `Submission` column and no Alembic migration, since every input already lives in `Submission.answers`; this mirrors `_innovation_context`'s re-derivation pattern rather than #0002's persisted-column approach. Rendered on all three result surfaces (web via a new shared `_result_now_next.html` partial included inside `_persona_card.html`, PDF via the same partial, and both email bodies via inline markup) directly below the persona description and above `Natural allies`/`Friends`/`Necessities` — moved here from an initial ship as its own card below the innovation-curve block, per follow-up feedback — guarded so an unanswered source question renders that one statement as absent rather than a half-built sentence. No organisation-register copy was supplied for this item — the `_organisation` override mechanism is wired and validated but left unused, so the org track currently renders the same individual-register copy; Tom/Rob/Andrew can add `now_organisation`/`next_organisation` and per-option `statement_phrase_organisation` later with no code change
- Tests: `tests/test_loader.py` (+18 for `statement_phrase`/`statement_phrase_organisation` validation and the `now_next` construct, incl. its optional `_organisation` overrides), `tests/test_persona.py` (+16 for `_join_phrases`, `_statement_phrase`'s fallback chain, and `resolve_now_next` worked examples against the real survey — both statements, per-statement `None` on a missing source answer, and the no-`now_next`/organisation-fallback defensive paths), `tests/test_real_survey_e2e.py` (+5 — the Now/Next block's position inside the persona card, between the description and Natural allies, the PDF/email templates rendering the statement text, and ampersand auto-escaping in topic labels on the PDF and email-HTML surfaces) — 309 tests total

---

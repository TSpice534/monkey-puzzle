---
id: 0004
title: Real persona and innovation-curve copy (Natural Allies/Friends/Necessity)
type: feature
status: todo
created: 2026-07-15
branch:
---

## Request
Two real content docs landed from Rob/Andrew: `docs/PROFILES-TEMPLATE.md` (all 9
personas' final Tag Line, Focus/Wording copy, and a 3-way relationship model — Natural
Allies / Friends / Necessity) and `docs/INNOVATION-TEMPLATE.md` (tagline + description
for all 5 Rogers-curve bands). Replace/add this content to the results page, on top of
the persona card (#0003) and Innovation-Curve card (#0002) already built.

Confirmed with Tom (2026-07-15):
- Keep the Laggard tagline exactly as given, **"You are a Laggard. Wanker."** —
  verbatim, not softened.
- Clean up the templates' typos while bringing content in (Coorperator→Cooperator,
  implimentsolutions→implement solutions, organsation→organisation, activly→actively,
  distruptor→disruptor, feasability→feasibility, a stray double-period in Accountant's
  individual wording) — same approach as the 2 typos already fixed in #0003.
- The new **"Necessity"** relationship is a genuine reframe, not a rename of "battlers"
  (previously "likely friction"). Values read as complementary needs (e.g. Advocate's
  Necessity is Cooperator — who executes what Advocate opens up), not rivals. Display
  copy must change to reflect "who you need," not friction.

## Investigation
Direct reads of both content docs, `_persona_card.html`, `app/templates/pdf/result.html`,
`app/templates/email/result.html`/`result.txt`, `app/survey/loader.py`'s
persona/innovation_curve validation, and the current `content/survey.yaml` personas
block (via an Explore agent, key lines confirmed directly).

**Personas (`content/survey.yaml`, all 9):**
- `tagline` and `description` get replaced with the new copy (Tag Line column;
  description built from Focus + Wording (Individual), cleaned of typos — Organisation
  wording exists too but the schema's `description` field is audience-neutral prose, not
  the `label`/`label_organisation` per-option pattern used elsewhere; a per-audience
  persona description would be new schema surface not asked for here, so default to the
  Individual wording for `description` unless told otherwise).
- `brethren`/`besties`/`battlers` (lists of persona ids, validated in
  `loader.py::_validate_personas` lines ~79-87, every entry must be an existing persona
  id) get **renamed to `natural_allies`/`friends`/`necessity`** — not just re-valued.
  Renaming (rather than keeping old field names with new meaning) is the clearer choice
  since Rob/Andrew will maintain this YAML going forward and "battlers" would be
  actively misleading once it holds "who you need" data. Most personas have 1 value per
  column; Communicator and Entrepreneur have 2 each for allies/friends (comma-separated
  in the template, e.g. Communicator's Natural Allies = "Advocate / Accountant") — the
  existing list-shaped field already supports this, no cardinality change needed.
- `case_studies`/`resources` are untouched — no new content given for them, stay as
  today's placeholders.

**`_persona_card.html`** (lines ~20-30, reused verbatim by web result page AND PDF):
the literal strings "(natural allies)", "(good collaborators)", "(likely friction)" are
in the template markup, not just code comments. Update the three blocks to
`{{ persona.natural_allies }}` / `{{ persona.friends }}` / `{{ persona.necessity }}`
with new glosses — recommend "(natural allies)" and "(friends)" stay close to current,
and "(likely friction)" becomes something like "(who you need)".

**Email (`app/templates/email/result.html`/`result.txt`)**: does NOT include
`_persona_card.html` — hand-rolled, currently only name/tagline/description +
innovation band. This is a pre-existing gap (relationships were never in email, even
before this request). Default: leave that gap as-is — don't newly add
allies/friends/necessity to email, since Tom didn't ask for that and it's not a
regression. If Tom wants email parity here too, that's a fast, additive follow-up.

**Innovation-Curve bands (`content/survey.yaml`'s `innovation_curve.bands`, validated in
`loader.py::_validate_innovation_curve` lines ~352-398)**: currently only
`name`/`min`/`max`/`colour` per band — no tagline/description field exists. Need to add
`tagline`/`description` (required non-empty strings, same validation shape as personas)
to the schema, map the template's singular band names to the existing plural ones
(Innovator→Innovators, "Early adaptor"→Early Adopters, Early majority→Early Majority,
Late Majority→Late Majority, Laggard→Laggards), and thread them through
`app/survey/routes.py::_innovation_context()` (currently returns only
`band`/`score`/`colour`) into `_result_innovation.html` (currently band name + colour
swatch only).

**Innovation-Curve surface parity**: #0002 established an explicit "must appear on web +
PDF + email, not web-only" requirement for the band card. The new tagline/description
should follow that same precedent — extend `_result_innovation.html` (shared web+PDF)
and the inline email markup in `result.html`/`result.txt` to show the new copy, not
just the band name.

## Notes
- Two defaults chosen that Tom can override: (1) persona relationships
  (allies/friends/necessity) stay web+PDF only, not extended to email (pre-existing gap,
  not a regression); (2) persona `description` uses the Individual wording only —
  audience-specific persona descriptions would be new schema surface not asked for here.
- No existing test should need to keep asserting on the old `brethren`/`besties`/
  `battlers` field names or "likely friction" copy — repoint them, same pattern as the
  `documenter`→`accountant` rename in #0002.
- Depends on #0002 and #0003 both being on `dev` (both are, as of this filing).

---
id: 0027
title: Update persona Natural Ally / Friends / Necessity relationship table
type: change
status: todo
created: 2026-08-30
branch:
---

## Request
Update the persona relationship table (Natural Ally / Friends / Necessity per role) in
content/survey.yaml and docs/PROFILES-TEMPLATE.md to the table below. Confirmed with Tom:
"Developer"/"Advocate" in his source table are leftover pre-#0018-rename names, resolved to
Inventor/Architect; typos (Connecter, Cooperater, Inventer) normalized to the real ids; the
following 4 are genuine intentional relationship changes, not typos:
- Inventor.necessity: implementer -> architect
- Communicator.necessity: implementer -> entrepreneur
- Connector.necessity: communicator -> inventor
- Cooperator.necessity: inventor -> connector

Full resolved table:

| id | natural_allies | friends | necessity |
|---|---|---|---|
| accountant | communicator | inventor | implementer |
| implementer | entrepreneur | accountant | activist |
| inventor | architect | connector | architect |
| architect | communicator | inventor, connector | cooperator |
| communicator | architect, accountant | connector, cooperator | entrepreneur |
| activist | cooperator | connector | communicator |
| connector | entrepreneur | cooperator | inventor |
| cooperator | connector | communicator | connector |
| entrepreneur | implementer, cooperator | communicator, architect | accountant |

## Investigation
Pure data change in content/survey.yaml (persona blocks, natural_allies/friends/necessity
fields, ~lines 32-221) plus docs/PROFILES-TEMPLATE.md's matching table (source-of-truth doc,
update alongside per the pattern #0018 set). app/survey/loader.py:91-98 validates these
reference known persona ids — all target ids already exist, validation will pass unchanged.
app/templates/survey/_persona_card.html renders these with no hardcoded values, nothing to
touch there. Checked tests/test_loader.py and tests/test_persona_copy_verification.py for
hardcoded relationship values that would need updating — none found; both test against
fixtures/fields unaffected by this change.

## Notes
Only Inventor's necessity value now equals its own natural_ally-of-natural_ally... no, more
precisely: inventor.necessity becomes "architect", same as inventor.natural_allies —
duplicate value in two different relationship categories for the same persona. Not
necessarily wrong (Tom confirmed this row explicitly), just flagging since it's the one row
where two categories point at the same id — worth a glance on the result page card to make
sure the copy still reads sensibly with Architect appearing twice.

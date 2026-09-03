---
id: 0028
title: Turn role-relationship lines into full sentences (Andrew's copy review)
type: change
status: shipped
created: 2026-08-30
branch: feature/role-relationship-sentence-copy
---

## Request
On the "Your sustainability who" result page, replace the bare "Natural allies: Role, Role"
/ "Friends: Role, Role" / "Necessities: Role, Role" lines with full sentences, per Andrew's
copy review (Tom relayed, two gaps resolved with Tom):

- Natural allies: "You probably work closely with a/an {role}."
- Friends: "You might find support from a/an {role}."
- Necessities: "Collaborating with a/an {role} would be a good way to improve impact."
  (Andrew's typed text was missing words here — Tom confirmed "would be a good way to
  improve impact" as the intended full sentence.)

For personas with 2 roles in a category (Architect.friends, Communicator.natural_allies,
Communicator.friends, Entrepreneur.natural_allies, Entrepreneur.friends — per #0027's
values), join with "and" and drop the article: "You probably work closely with {role1} and
{role2}."

## Investigation
Only render site is app/templates/survey/_persona_card.html:17-36 (the Natural
allies/Friends/Necessities `<p>` blocks). No existing macro builds sentence-style role
copy — persona_description (survey/_macros.html) only covers the main blurb — so this needs
new inline Jinja or a small macro, singular vs. joined-pair logic per list length.

Grammar gap beyond what Andrew flagged: templates use "a {role}" but 6 of 9 persona names
start with a vowel sound (Accountant, Implementer, Inventor, Architect, Activist,
Entrepreneur) and need "an", vs. "a" for Communicator/Connector/Cooperator. Compute this
dynamically from the first letter rather than hardcoding per persona.

tests/test_persona_copy_verification.py currently asserts comma-joined rendering of
friends: [connector, cooperator] for communicator/entrepreneur — will need updating to
match new sentence copy. Check test_real_survey_e2e.py and
test_innovation_curve_visualisation_verification.py too for any "Natural allies:"/"Friends:"
/"Necessities:" label assertions.

## Notes
Depends on #0027 (role-relationship table update) landing first if both are shipped close
together — this item's sentences read out the same role lists #0027 is changing the values
of, so shipping this before #0027 lands would just mean sentence copy reads correctly but
still shows the old New pairings until #0027 merges too. No hard blocking order required
(they touch different template regions), just worth landing both before the next
deploy/demo so the copy and the values match.

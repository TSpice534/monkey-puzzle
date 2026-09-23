---
id: 0034
title: Footer credit line + obfuscated "Email Us" contact link
type: feature
status: todo
created: 2026-09-23
branch:
---

## Request

Add to footer:
- Credit "Developed by The Very Good Solutions Company".
- "Email Us" link for feedback etc., sending to "rob@robvanwegen.nl". Keep the email
  address hidden on the page.

## Investigation

Source: `app/templates/base.html` (read directly — no CLAUDE.md section covers the
footer specifically) plus `app/__init__.py`'s CSP setup (referenced in `CLAUDE.md`'s Tech
Stack table under Frontend).

- **Footer today** (`app/templates/base.html:48-53`): a single `<footer>` with one
  `<span class="text-muted small">The Monkey Puzzle</span>` inside a `.container`. No
  credit line, no contact link exists yet.
- **Credit line**: add "Developed by The Very Good Solutions Company" alongside the
  existing "The Monkey Puzzle" text in the footer — plain static text, no open questions.
- **"Email Us" link, obfuscated**: Tom confirmed he wants the address kept out of the raw
  HTML/view-source, not just off the visible page text — so a plain
  `mailto:rob@robvanwegen.nl` href isn't enough. The CSP already supports nonce'd inline
  scripts for exactly this kind of small progressive-enhancement snippet:
  `app/__init__.py` generates a per-request `g.csp_nonce` (before_request) and injects
  `script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net`; the nonce is exposed to
  every template via the `csp_nonce` context processor. Existing pattern to copy:
  `app/templates/survey/result.html:83` and `:119`, and
  `app/templates/survey/_question_profile_pair.html:49` all use
  `<script nonce="{{ csp_nonce }}">...</script>` for small inline snippets under this same
  CSP. Follow that pattern for the footer: render a link with no `href` (or a `#` /
  `role="button"` placeholder) plus a nonce'd inline script that builds the `mailto:`
  address at render time (e.g. from two joined string parts or a simple character-code
  build) and sets `href` on load — keeps the raw address out of the page source while
  requiring no new CSP directive changes and no external JS file.
- **No backend involvement**: this is a static footer link, unrelated to the existing
  `MAIL_SERVER`/`email_utils.py` outbound-mail feature (that sends the *result* PDF by
  email; this is just a contact link) — no config or route changes needed.

## Notes

- Tom confirmed: obfuscate the address in the HTML source (not just hide it from visible
  page text), accepting the small JS addition to the footer under the existing CSP nonce
  mechanism.
- Exact obfuscation technique (split-string join vs. char-code build vs. reversed string)
  is an implementation detail for `/ship` — any of the standard lightweight patterns works
  under the existing nonce'd `<script>` approach; no further scoping needed here.
- Footer currently has no dividers/layout between text items — `/ship` should keep the
  Bootstrap-utility-class style already used elsewhere in `base.html` (e.g. `text-muted
  small`) rather than introducing new custom CSS unless needed for layout.

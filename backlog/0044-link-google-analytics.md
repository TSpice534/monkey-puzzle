---
id: 0044
title: Link Monkey Puzzle to Google Analytics
type: feature
status: todo
created: 2026-09-30
branch:
---

## Request
Link the Monkey Puzzle to Google Analytics so we can see traffic and how people move through the survey.

## Investigation
Sourced from docs plus a few targeted greps of `app/__init__.py`, `base.html` and `config.py`.

- Site is no-login, public and anonymous. No analytics, cookie banner or privacy page exists today.
- Every page extends `app/templates/base.html`, which already has a nonce'd inline script and a `{% block scripts %}`. The GA snippet fits there using `csp_nonce`.
- CSP is set in `app/__init__.py` (`set_security_headers`, ~lines 95-120) and currently blocks GA:
  - `script-src` allows only self, nonce and cdn.jsdelivr.net. Needs `https://www.googletagmanager.com`.
  - `img-src` is `'self' data:`. Needs `https://*.google-analytics.com` and `https://*.analytics.google.com`.
  - No `connect-src`, so `default-src 'self'` applies. Needs `https://*.google-analytics.com`, `https://*.analytics.google.com` and `https://www.googletagmanager.com`.
- Config pattern: env vars read in `config.py` (e.g. `MAIL_*`). Add `GA_MEASUREMENT_ID`, unset by default, so dev, tests and forks (MIT, open source) send nothing. Render the snippet and widen the CSP only when it is set.
- Tests (pytest, `tests/`): snippet absent when unset, present when set, CSP widened only when set.
- Deploy: set the env var in the `monkeypuzzle` systemd unit on the VPS and document it in `DEPLOY.md`. Manual step for Tom.

## Notes
Decision (2026-09-30): GA4 with an unobtrusive consent banner, not cookieless.

Scope:
- GA4 via gtag, loaded only after the visitor accepts. Consent Mode v2 with `analytics_storage` defaulting to denied. No GA request or cookie before consent.
- Small, low-key banner (bottom strip, Accept / Decline equally prominent, no dark patterns). Choice stored in a first-party cookie or localStorage, with a way to change it later (footer link).
- Banner script must carry `csp_nonce`, or be a static file under `'self'`. Keep the survey step pages light: they are currently scriptless (see CONTEXT.md, #0013).
- Redact `/result/<token>` before anything goes to Google (override `page_location` / `page_path`).
- CSP widening and the GA snippet only when `GA_MEASUREMENT_ID` is set.
- Add a short privacy note (what GA collects, cookies used, how to withdraw), linked from the banner and footer. No privacy page exists yet.

Still open:
- Who owns the GA4 property and measurement ID, Tom or Rob/Andrew?
- GA4 only, or GTM? (Default: GA4 only, simpler CSP.)

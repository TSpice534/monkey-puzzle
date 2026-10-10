---
id: 0045
title: Footer 'Email Us' link fails contrast (4.26:1)
type: bug
status: todo
created: 2026-10-10
branch:
---

## Request
The footer 'Email Us' link is Bootstrap default blue #0d6efd on #f8f9fa, 4.26:1, below the 4.5:1 AA minimum. Make it readable in light and dark and visually consistent with the brand.

## Investigation
Found by axe-core against the running app (light mode; dark passes). Footer is in `app/templates/base.html` (`#footer-email-link`); a 44px tap-target rule already exists in `app/static/css/theme.css` (`.footer a`). Use the dark brand green (`--brand-accent`) with an underline, defined for both appearances.

## Notes
Route: `/quick-ship`. Per DESIGN.md contrast targets. Do not change the mailto target or the obfuscation from #0034.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

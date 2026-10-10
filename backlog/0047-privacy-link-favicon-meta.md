---
id: 0047
title: Add privacy link, favicon and home-page meta description
type: feature
status: todo
created: 2026-10-10
branch:
---

## Request
The site has no privacy link, no favicon and no meta description on the home page. Add all three.

## Investigation
Grep of `app/templates` finds no privacy page or link; `og:` tags exist only on `survey/result.html`. Footer is in `base.html`. A privacy page needs wording from Tom or Rob; see #0044 (analytics and the consent-banner decision) because a privacy page should cover whatever #0044 ends up collecting.

## Notes
Route: `/ship` (new page plus template changes). Open question: who writes the privacy copy. Do not invent legal text.

Source: design review of 2026-10-10 (Playwright walkthrough, axe-core, apple-design, web-design-guidelines, redesign and taste audits). Design reference: DESIGN.md at the repo root.

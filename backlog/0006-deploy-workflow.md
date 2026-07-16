---
id: 0006
title: Deploy workflow, script and guide for monkey-puzzle
type: feature
status: in-progress
created: 2026-07-15
branch: feature/deploy-workflow
---

## Request

Deploy workflow, script, and guide for getting monkey-puzzle up and running on the server,
similar to Donut Toolkit, including a new GitHub repo to push to.

## Investigation

**monkey-puzzle's own docs already scope this (`docs/PRODUCTION-PLAN.md` lines 46, 167-169):**
> Deploy pattern: clone Donut's `deploy/donut.service`, `deploy/nginx.conf`, `deploy.sh.example`
> as a new systemd service on the same Infomaniak VPS; `dev`-first branch discipline; manual
> deploy via SSH (read-only server access — hand deploy steps to Tom, never run mutating server
> commands).

**Current state:**
- `git remote -v` in monkey-puzzle returns nothing — no GitHub repo exists yet. Root `CLAUDE.md`'s
  own Git Workflow section already says "push to origin dev (once a remote exists)" — it's been
  waiting on this.
- No `deploy/` directory, no `deploy.sh.example`, no deploy guide anywhere in the repo.

**Donut Toolkit's actual deploy setup (the pattern to clone), read directly:**
- `deploy/donut.service` — systemd unit: `User=donut`/`Group=donut` service account, Gunicorn
  bound to a Unix socket (`donut.sock`), `EnvironmentFile=/opt/donut-toolkit/.env`,
  `Restart=on-failure`.
- `deploy/nginx.conf` — one file holding **all** deployments on this VPS: a dedicated
  `edi-toolkit.impalamusic.org` server block, plus a `tomspice.co.uk` server block with
  path-based `location` blocks per client (`/impala-edi-toolkit`, `/gecop-toolkit`), each with
  its own `/static/` alias and `proxy_pass` to that app's socket, `X-Forwarded-Prefix` set to the
  path. **Given Tom's choice (subpath, not subdomain), monkey-puzzle's deploy adds a third such
  path block to this same file** — e.g. `/monkey-puzzle` and `/monkey-puzzle/static/` — reusing
  the existing `tomspice.co.uk` cert (Certbot already covers this domain, confirmed by the
  existing blocks), no new DNS/cert step needed.
- `deploy.sh.example` — copied to a gitignored `deploy.sh` per server, `SERVICE=` set to that
  server's unit name; does `git pull` → `pip install -r requirements.txt` → `flask db upgrade` →
  `sudo systemctl restart $SERVICE`. **Must ship monkey-puzzle's own copy pre-gitignored from
  day one** — Donut hit a real incident (documented in its `INFOMANIAK-DEPLOY.md`, "One-time
  gotcha") where `deploy.sh` was originally tracked, and a `git pull` on a multi-tenant box
  overwrote another deployment's `SERVICE=` value, restarting the wrong systemd unit (happened
  twice). Add `deploy.sh` to `.gitignore` from the start; ship `deploy.sh.example` only.
- `INFOMANIAK-DEPLOY.md` — the step-by-step guide: VPS/DNS context (skippable here — same VPS,
  same domain, no new DNS), SSH hardening (already done, one-time, not per-app), service-account
  creation, dependency install (Donut's WeasyPrint/libpango system packages — monkey-puzzle needs
  the same, it also uses WeasyPrint per its own `CLAUDE.md`), clone-to-`/opt/`, venv +
  `requirements.txt`, `.env` (SECRET_KEY, no admin/CLIENT_CONFIG vars needed — monkey-puzzle has
  no auth/admin/multi-client config), migrations, systemd service install, Nginx site reload,
  verify, then "Part 12 — Deploying Code Updates" (the steady-state `deploy.sh` workflow) and a
  troubleshooting/cheat-sheet section.
- The VPS is confirmed **multi-tenant already** (donut/gecop/superstruct services coexist) — this
  becomes a fourth. `useradd`, `apt install` system packages, and the initial `git clone` all need
  `sudo`, which is a one-time manual step for Tom per the read-only server-access rule — the
  guide documents these as commands *for Tom to run*, never executed by Claude against the VPS.

**Differences from Donut's setup that the new guide/script must reflect (monkey-puzzle has no
auth, no admin, no multi-client config):**
- No admin-user creation step (Part 7 in Donut's guide) — monkey-puzzle's `Submission` model is
  anonymous, no `User` model exists.
- No `CLIENT_CONFIG`/`ADMIN_EMAIL` env vars — monkey-puzzle's `.env` only needs `SECRET_KEY`,
  `FLASK_ENV`/`HTTPS`, and the optional `MAIL_*` vars (email-a-copy is opt-in, per its own
  `CLAUDE.md`).
- Static file alias path differs (`app/static/` — confirmed monkey-puzzle's actual static root
  from its own `CLAUDE.md` project-structure listing).
- Systemd unit + socket naming: `monkeypuzzle.service` / `monkeypuzzle.sock`, `User=monkeypuzzle`
  service account, `WorkingDirectory=/opt/monkey-puzzle`, entry point `monkeypuzzle:app` (matches
  `monkeypuzzle.py` entry point named in its own `CLAUDE.md`).

**GitHub repo:**
- monkey-puzzle's own `CLAUDE.md` already states "This repo is public-facing" and "open source
  (MIT)" — a public repo under the same account as `donut-toolkit`
  (`https://github.com/TSpice534/`) is the natural default, named `monkey-puzzle`.
- Creating the repo (`gh repo create`) and pushing are real, externally-visible, one-way actions
  — out of scope for this filing step. This ticket should have `/ship` produce the deploy
  script/guide/`deploy/` files and stop at "ready to push"; actually creating the GitHub repo,
  pushing, and running the guide's commands on the VPS all remain manual/confirmed steps handed
  to Tom, consistent with prior guidance to never mutate the production VPS and to keep server
  deploys manual/SSH-driven.

**Decision from Tom:** host at a **subpath** on `tomspice.co.uk` (`/monkey-puzzle`), joining
`/impala-edi-toolkit` and `/gecop-toolkit` in the same Nginx server block and reusing its
existing cert — not a new subdomain or separate domain.

## Notes

- Deliverables: `deploy/monkeypuzzle.service`, a `/monkey-puzzle` path addition to (a copy of, or
  coordinated edit to) Donut's `deploy/nginx.conf` pattern, `deploy.sh.example` (+ `.gitignore`
  entry for `deploy.sh` from the start), and a `DEPLOY.md`/`INFOMANIAK-DEPLOY.md`-style guide
  scoped to monkey-puzzle's simpler no-auth stack.
- Open question to confirm at `/ship` time: does the existing `tomspice.co.uk` Nginx config file
  live only on the VPS (read-only, Tom edits it by hand per the guide) or should monkey-puzzle's
  repo carry its own `deploy/nginx.conf` with just its own block, to be manually merged into the
  live multi-tenant file? Donut's own `deploy/nginx.conf` already holds all three clients' blocks
  in one committed file, which is arguably the wrong home for another app's config — worth a
  quick call before writing it.
- Actually creating the GitHub repo and running any command against the VPS are **not** part of
  this ticket's automated build — hand those steps to Tom explicitly when `/ship` completes.

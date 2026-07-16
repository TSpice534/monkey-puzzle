# Deploying The Monkey Puzzle on Infomaniak

_Step-by-step guide for adding The Monkey Puzzle as a new service on the **same**
Infomaniak VPS that already runs the Donut Toolkit, served at a subpath on the existing
`tomspice.co.uk` domain._

Every server command below is written as an instruction **for Tom** to run over SSH.
Server access here is read-only for automation — nothing in this guide is run by an
agent against the VPS.

---

## Overview

The stack being deployed:

```
Internet → Nginx (port 443, existing cert) → Gunicorn (Unix socket) → Flask app
                                                                      ↑
                                                                   SQLite
```

Nginx terminates HTTPS and serves static files. Gunicorn runs the Flask app as a
persistent background process managed by systemd — the same pattern as the Donut
Toolkit, just a second, independent service on the same box.

**This is not a new VPS and not a new domain.** The Monkey Puzzle is added to the
Infomaniak VPS that already hosts the Donut Toolkit, served at
`https://tomspice.co.uk/monkey-puzzle`. Since `tomspice.co.uk` already has a valid TLS
certificate (issued for the Donut Toolkit's subpath deployments), there is **no DNS
change and no Certbot step** — this guide reuses the existing cert.

**User accounts on the server:**
- `ubuntu` — the SSH login account; has sudo privileges. You do everything from here.
- `monkeypuzzle` — app-only service account; runs Gunicorn. Never SSH into this account.

---

## Prerequisites (already done for Donut Toolkit — one-time per box)

These were completed when the Donut Toolkit was first deployed to this VPS and don't
need repeating:

- SSH hardening (`PermitRootLogin no`, `PasswordAuthentication no`)
- UFW firewall (`OpenSSH` + `Nginx Full` allowed)
- Nginx installed and already serving `tomspice.co.uk` (plus `edi-toolkit.impalamusic.org`)

If any of these aren't in place on this box, see the Donut Toolkit's
`INFOMANIAK-DEPLOY.md` (Parts 3–4) before continuing.

---

## Part 1 — Create the `monkeypuzzle` service account

```bash
sudo useradd -m -s /bin/bash monkeypuzzle
```

No SSH key setup needed — it's only used by systemd to run the Gunicorn process.

---

## Part 2 — System dependencies

Most of these are already installed from the Donut Toolkit setup; re-running `apt
install` is a harmless no-op for anything already present:

```bash
sudo apt install -y \
    python3 python3-venv python3-pip \
    nginx \
    git \
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libharfbuzz0b libfontconfig1 libgdk-pixbuf-2.0-0
```

The Monkey Puzzle needs the `libpango`/`libcairo`-family libraries for **both**
WeasyPrint (PDF report) and CairoSVG (the OpenGraph share image) — a slightly wider use
of the same libraries than Donut Toolkit needs for WeasyPrint alone.

---

## Part 3 — Clone the repo

```bash
sudo git clone https://github.com/TSpice534/monkey-puzzle.git /opt/monkey-puzzle
```

> The repo must already exist on GitHub and have `dev`/`main` pushed before this step
> works — that's a manual step for Tom, not covered by this guide (see "Hand back to
> Tom" at the end).

---

## Part 4 — Virtual environment and dependencies

```bash
cd /opt/monkey-puzzle
sudo python3 -m venv venv
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -r requirements.txt
```

---

## Part 5 — Logs directory and ownership

```bash
sudo mkdir -p /opt/monkey-puzzle/logs
sudo chown -R monkeypuzzle:monkeypuzzle /opt/monkey-puzzle
```

The `monkeypuzzle` user owns the app directory so Gunicorn can write logs and the
SQLite database.

---

## Part 6 — Configure environment variables

```bash
sudo -u monkeypuzzle nano /opt/monkey-puzzle/.env
```

The Monkey Puzzle has no accounts and no admin layer, so its `.env` is shorter than
Donut Toolkit's — no `CLIENT_CONFIG`, no `ADMIN_EMAIL`, no auth vars:

```env
# --- Flask / Security ---
SECRET_KEY=replace-with-a-long-random-string
FLASK_ENV=production
HTTPS=true

# --- Database (optional) ---
# Leave DATABASE_URL unset to use SQLite at /opt/monkey-puzzle/monkeypuzzle.db —
# fine for expected traffic. psycopg2 is bundled if Postgres is wanted later:
# DATABASE_URL=postgresql://monkeypuzzle:password@localhost/monkeypuzzle

# --- Email (optional) ---
# The "email me a copy" feature is opt-in and no-ops with a flash message if these
# are left unset:
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USE_TLS=true
# MAIL_USERNAME=noreply@example.com
# MAIL_PASSWORD=your-google-app-password
```

**Generating a `SECRET_KEY`** — run this on the server and copy the output:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**This is not optional.** The app refuses to boot under Gunicorn if `SECRET_KEY` is left
at the dev default — `config.py`'s guard is active whenever the app isn't running in
debug mode, and it will raise on startup rather than silently run insecurely. This is
intentional; don't work around it.

`HTTPS=true` is what makes `SESSION_COOKIE_SECURE` true, so session cookies only travel
over HTTPS — required since this is served over `https://tomspice.co.uk`.

**Do not add `FLASK_DEBUG` to `.env`.** As an aside: the committed `.flaskenv` sets
`FLASK_DEBUG=1` plus a dev SQLite `DATABASE_URL` and a macOS `DYLD_LIBRARY_PATH`. The
Flask CLI auto-loads `.flaskenv` for commands like `flask db upgrade` (Part 7) — harmless
there — but Gunicorn does **not** load `.flaskenv`, so the running service stays in
production mode regardless.

---

## Part 7 — Run database migrations

Unlike Donut Toolkit, there's no admin-user creation step here — The Monkey Puzzle is
anonymous, with no `User` model at all.

```bash
sudo -u monkeypuzzle bash -c "cd /opt/monkey-puzzle && source venv/bin/activate && flask db upgrade"
```

---

## Part 8 — Set up Gunicorn as a systemd service

The service file is already in the repo. Copy it into place:

```bash
sudo cp /opt/monkey-puzzle/deploy/monkeypuzzle.service /etc/systemd/system/monkeypuzzle.service
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable monkeypuzzle
sudo systemctl start monkeypuzzle
sudo systemctl status monkeypuzzle
```

You should see `Active: active (running)`. If it shows `failed`, check the logs:

```bash
sudo journalctl -u monkeypuzzle -n 50
# or
sudo cat /opt/monkey-puzzle/logs/gunicorn.log
```

---

## Part 9 — Nginx (merge the snippet into the live config)

The Monkey Puzzle does **not** get its own Nginx site file — it's added as two more
`location` blocks inside the same multi-tenant `server { server_name tomspice.co.uk; }`
block that already serves `/impala-edi-toolkit` and `/gecop-toolkit`.

Open the live config:

```bash
sudo nano /etc/nginx/sites-available/donut
```

Paste both `location` blocks from `deploy/nginx-monkeypuzzle.conf` into the existing
`tomspice.co.uk` `server {}` block, alongside the `/impala-edi-toolkit` and
`/gecop-toolkit` blocks already there. **Do not create a new `server {}` block or a new
site file**, and don't copy any of Donut's other client blocks into this repo.

Test and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Then add Nginx to the service's group so it can read the Unix socket:

```bash
sudo usermod -aG monkeypuzzle www-data
sudo systemctl restart nginx
```

---

## Part 10 — TLS

**Skip this entirely.** The `tomspice.co.uk` certificate already covers this path — no
Certbot, no new certificate, no DNS change. Adding a new path under an already-certified
domain doesn't require re-issuing anything.

---

## Part 11 — Verify

1. Browse to `https://tomspice.co.uk/monkey-puzzle` — the home page should render over
   HTTPS.
2. Complete the survey start → finish, and confirm a persona + radar chart render on the
   result page.
3. Download the PDF report.
4. If `MAIL_*` was set in `.env`, trigger the optional "email me a copy" and confirm it
   arrives.
5. **Crucially:** click around and confirm every link/redirect stays under
   `/monkey-puzzle/...`. If any link points at the domain root instead, the
   `X-Forwarded-Prefix` → `ProxyFix` path isn't taking effect — check that the Nginx
   block sets the header (Part 9) and that the service was restarted after any config
   change.

---

## Part 12 — Deploying code updates (steady state)

First time only, turn the committed template into this server's real deploy script:

```bash
cd /opt/monkey-puzzle
cp deploy.sh.example deploy.sh
nano deploy.sh   # set SERVICE=monkeypuzzle
```

From then on, every deploy is one command:

```bash
cd /opt/monkey-puzzle && sudo bash deploy.sh
```

This pulls the latest code, installs any new dependencies, runs pending migrations, and
restarts the Gunicorn service.

**Gitignore gotcha — read this before ever touching `deploy.sh` on this box.**
`deploy.sh` is gitignored (see `.gitignore`), so a `git pull` can never silently reset
it. This is deliberate: on the Donut Toolkit's shared, multi-tenant VPS, running
`git checkout -- deploy.sh` restored the tracked default's `SERVICE=` value and restarted
the *wrong* client's systemd unit — this happened twice. **Never run
`git checkout -- deploy.sh` on this server.** If `deploy.sh` is ever missing or looks
wrong, recreate it from `deploy.sh.example` and set `SERVICE=monkeypuzzle` again — don't
reach for `git checkout`. Keep this server's `deploy.sh` untracked, permanently.

---

## Troubleshooting

### App won't start (systemd shows `failed`)

```bash
sudo journalctl -u monkeypuzzle -n 100 --no-pager
sudo cat /opt/monkey-puzzle/logs/gunicorn.log
```

Common causes:
- Missing or malformed `.env`
- `SECRET_KEY` still set to the dev default — the app refuses to boot in production
- Wrong entry point — verify `monkeypuzzle:app` resolves:
  ```bash
  cd /opt/monkey-puzzle && source venv/bin/activate && python3 -c "from monkeypuzzle import app; print('ok')"
  ```

### 502 Bad Gateway from Nginx

The Gunicorn socket isn't running, or Nginx can't reach it.

```bash
sudo systemctl status monkeypuzzle
ls -la /opt/monkey-puzzle/monkeypuzzle.sock  # should exist
```

If the socket exists but Nginx still can't reach it, confirm `www-data` is in the
`monkeypuzzle` group (Part 9):

```bash
sudo usermod -aG monkeypuzzle www-data
sudo systemctl restart nginx
```

### Links point at the domain root instead of `/monkey-puzzle/...`

The `X-Forwarded-Prefix` header isn't reaching the app, or `ProxyFix` isn't applying it.
Check the Nginx `location /monkey-puzzle` block still sets
`proxy_set_header X-Forwarded-Prefix /monkey-puzzle;` (Part 9), then restart the
service.

### WeasyPrint / PDF errors

Usually a missing native library. Re-run Part 2's `apt install` — the `libpango*`
family is required for both the PDF report and the PNG share image.

---

## Cheat-sheet

| Task | Command |
|---|---|
| Deploy new code | `cd /opt/monkey-puzzle && sudo bash deploy.sh` |
| View app logs | `sudo journalctl -u monkeypuzzle -f` |
| Restart app | `sudo systemctl restart monkeypuzzle` |
| Test Nginx config | `sudo nginx -t` |
| Reload Nginx | `sudo systemctl reload nginx` |

---

## Hand back to Tom (manual, out of scope for this build)

1. Create the GitHub repo `TSpice534/monkey-puzzle` (public, MIT) and push `dev`/`main`.
   The clone URL used throughout this guide
   (`https://github.com/TSpice534/monkey-puzzle.git`) assumes this exact name on the same
   account as `donut-toolkit` — confirm it when the repo is created.
2. Run Parts 1–11 above on the VPS as `ubuntu` (needs sudo).
3. First time only: `cp deploy.sh.example deploy.sh` and set `SERVICE=monkeypuzzle` on
   the box (Part 12).

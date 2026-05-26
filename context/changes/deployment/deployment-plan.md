# Railway Deployment Plan — corobimy

## Context

The corobimy Django 6 app was scaffolded (May 24, 2026) but has never been deployed. Infrastructure research (May 26, 2026) selected Railway as the MVP platform. This plan bridges the gap between the bare scaffold and a live Railway deployment, covering all code-level changes, platform wiring, and verification steps.

**Current blockers identified during exploration:**
- `uv` is not installed (project was bootstrapped with pip/venv instead); Railpack requires `uv.lock` for auto-detection
- No `pyproject.toml` or `uv.lock` — no lock file means Railpack falls back to `requirements.txt` (which also doesn't exist)
- `settings.py` uses SQLite, hardcoded `SECRET_KEY`, `DEBUG = True`, empty `ALLOWED_HOSTS`
- No `.gitignore` at repo root (`.venv/`, `db.sqlite3`, `.env` would be committed)
- No `railway.toml` or deployment config
- No `context/deployment/` directory

**Key infrastructure.md constraints carried forward:**
- `CONN_MAX_AGE = 60` must be set before first production deploy (risk: connection saturation)
- Migrations must be decoupled from the start command for any non-trivial schema changes (risk: mid-migration container kill)
- No CLI rollback — human must navigate the dashboard on broken deploys

---

## Phase 1 — Python Dependency Management (uv migration)

> Goal: replace pip/venv with uv so Railpack can detect `uv.lock` natively.

- [ ] **1.1** Install `uv` globally (Windows PowerShell):
  ```powershell
  winget install astral-sh.uv
  # OR: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  Verify: `uv --version` returns `0.x.x`.

- [ ] **1.2** Create `pyproject.toml` at repo root with project metadata and all runtime dependencies:
  ```toml
  [project]
  name = "corobimy"
  version = "0.1.0"
  requires-python = ">=3.13"
  dependencies = [
      "django>=6.0.5",
      "gunicorn>=23.0.0",
      "psycopg[binary]>=3.2.0",
      "dj-database-url>=2.3.0",
      "whitenoise>=6.9.0",
  ]

  [tool.uv]
  dev-dependencies = []
  ```

- [ ] **1.3** Generate the lock file:
  ```powershell
  uv sync
  ```
  Expected output: `uv.lock` created at repo root; `.venv/` recreated by uv.

- [ ] **1.4** Verify Django still starts:
  ```powershell
  uv run python manage.py check
  ```
  Expected: `System check identified no issues`.

  > **Edge case — uv not in PATH after install:** restart the terminal or run `$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")` before retrying.

---

## Phase 2 — Django Settings: Production Hardening

> Goal: make settings.py environment-variable driven, PostgreSQL-ready, and static-file aware.

All changes are in `corobimy/settings.py`. The file currently has hardcoded values; replace each section as follows.

- [ ] **2.1** Add `import os` and `import dj_database_url` at the top of `settings.py` (after the existing `from pathlib import Path` line).

- [ ] **2.2** Replace `SECRET_KEY` (line 23):
  ```python
  SECRET_KEY = os.environ['SECRET_KEY']
  ```
  > **Edge case — KeyError on local dev:** create a `.env` file (gitignored) with `SECRET_KEY=<local-dev-key>` and use `python-dotenv` OR keep the existing key as a local fallback via `os.environ.get('SECRET_KEY', '<existing-hardcoded-key>')` for development only. For production Railway injects the variable automatically.

- [ ] **2.3** Replace `DEBUG` (line 26):
  ```python
  DEBUG = os.environ.get('DEBUG', 'False') == 'True'
  ```

- [ ] **2.4** Replace `ALLOWED_HOSTS` (line 28):
  ```python
  ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
  ```

- [ ] **2.5** Add WhiteNoise to `MIDDLEWARE` immediately after `SecurityMiddleware` (line ~44):
  ```python
  'whitenoise.middleware.WhiteNoiseMiddleware',
  ```

- [ ] **2.6** Replace `DATABASES` (lines 75–80) with PostgreSQL + SQLite fallback for local dev:
  ```python
  DATABASES = {
      'default': dj_database_url.config(
          default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
          conn_max_age=60,
      )
  }
  ```
  `conn_max_age=60` satisfies the infrastructure.md risk register item on connection saturation.

- [ ] **2.7** Add static files config after `STATIC_URL = 'static/'`:
  ```python
  STATIC_ROOT = BASE_DIR / 'staticfiles'
  STORAGES = {
      'staticfiles': {
          'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
      },
  }
  ```

- [ ] **2.8** Verify settings parse correctly locally:
  ```powershell
  uv run python manage.py check --deploy
  ```
  Expected warnings only about HTTPS settings (acceptable at this stage — no TLS configured locally). No errors.

---

## Phase 3 — Repository Hygiene

> Goal: ensure no secrets, venv, or local DB are committed to git.

- [ ] **3.1** Create `.gitignore` at repo root:
  ```gitignore
  # Python
  __pycache__/
  *.py[cod]
  *.pyo

  # Virtual environment
  .venv/

  # Local DB
  db.sqlite3

  # Environment secrets
  .env
  .env.local

  # Static collected files
  staticfiles/

  # OS
  .DS_Store
  Thumbs.db
  ```

- [ ] **3.2** Confirm `.venv/` is not tracked:
  ```powershell
  git status
  ```
  `.venv/` must not appear as untracked. If it does, run `git rm -r --cached .venv` before committing.

- [ ] **3.3** Commit the Phase 1–3 changes:
  ```powershell
  git add pyproject.toml uv.lock .gitignore corobimy/settings.py
  git commit -m "migrate to uv, harden settings for railway deployment"
  ```
  > **Edge case — uv.lock is large:** Railway's Railpack caches the uv install layer between deploys if `uv.lock` is committed. Never gitignore it.

---

## Phase 4 — Railway CLI and Project Initialisation

> Goal: link the local repo to a Railway project; add Postgres.

- [ ] **4.1** Install Railway CLI (PowerShell):
  ```powershell
  npm i -g @railway/cli
  ```
  Verify: `railway --version`.

  > **Edge case — npm not installed:** install Node.js from `nodejs.org` first, or use `winget install OpenJS.NodeJS`.
  > **Alternative installer:** `iex ((New-Object System.Net.WebClient).DownloadString('https://install.railway.app'))` (Windows installer from `install.railway.app`).

- [ ] **4.2** Authenticate:
  ```powershell
  railway login
  ```
  Opens browser OAuth. After redirect, terminal shows `Logged in as <email>`.

  > **Edge case — headless / WSL environment:** use `railway login --browserless` to get a device code instead.

- [ ] **4.3** Initialise a new Railway project from repo root:
  ```powershell
  railway init
  ```
  Select "Create a new project" → name it `corobimy`. Railway writes `.railway/` config (do not gitignore this — it's a project pointer, not a secret).

- [ ] **4.4** Add PostgreSQL via Railway dashboard:
  - Open `railway.app` → select the `corobimy` project → **+ New** → **Database** → **PostgreSQL**
  - Railway provisions a Postgres service in EU West Metal (Amsterdam) and exposes `${{Postgres.DATABASE_URL}}`, `${{Postgres.PGHOST}}`, etc. as shared variables

  > **Edge case — EU region not Amsterdam by default:** in Railway dashboard → project settings → region, confirm "EU West Metal (Amsterdam)" is selected before adding the database. If another region was auto-selected, delete the Postgres service and re-add it after changing the project region.

- [ ] **4.5** (Optional but recommended) Create `railway.toml` at repo root to pin Railpack behaviour explicitly:
  ```toml
  [deploy]
  startCommand = "gunicorn corobimy.wsgi:application --bind 0.0.0.0:$PORT --workers 2"
  healthcheckPath = "/"
  healthcheckTimeout = 30

  [build]
  builder = "RAILPACK"
  ```
  > This overrides Railpack's auto-generated start command and prevents the risk of Railpack pointing to the wrong WSGI module after a beta toolchain update.

---

## Phase 5 — Environment Variables

> Goal: inject all production secrets into Railway before deploying.

Set via CLI (preferred, auditable) or Railway dashboard → Service → Variables.

- [ ] **5.1** Generate a production `SECRET_KEY`:
  ```powershell
  uv run python -c "import secrets; print(secrets.token_hex(50))"
  ```
  Copy the output — use it in the next step.

- [ ] **5.2** Set variables via Railway CLI:
  ```powershell
  railway variables set SECRET_KEY="<generated-above>"
  railway variables set DEBUG="False"
  railway variables set ALLOWED_HOSTS="<appname>.up.railway.app"
  railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}'
  ```
  > **`${{Postgres.DATABASE_URL}}` is Railway-proprietary template syntax** — it references the co-located Postgres service. Set it as a literal string in the dashboard (not the CLI, where shell expansion may corrupt it) by navigating to Service → Variables → Add Variable → value: `${{Postgres.DATABASE_URL}}`.

  > **Edge case — Railway CLI variable syntax on Windows PowerShell:** PowerShell may expand `${{...}}` patterns. Set `DATABASE_URL` via the dashboard UI to avoid shell interpolation issues.

- [ ] **5.3** Verify variables are set:
  ```powershell
  railway variables
  ```
  Expected: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL` all listed.

---

## Phase 6 — First Deploy

> Goal: ship the app to Railway and verify it's serving HTTP 200.

- [ ] **6.1** Collect static files locally to confirm WhiteNoise config is valid:
  ```powershell
  uv run python manage.py collectstatic --no-input
  ```
  Expected: files copied to `staticfiles/`. This directory is gitignored; Railway's build step will re-run `collectstatic`.

- [ ] **6.2** Run migrations locally against the local SQLite DB to confirm no migration errors:
  ```powershell
  uv run python manage.py migrate
  ```

- [ ] **6.3** Deploy (detached — returns immediately with a deployment URL):
  ```powershell
  railway up --detach
  ```
  Railway will:
  1. Run Railpack build (detects `uv.lock`, installs with `uv sync --frozen`)
  2. Run `python manage.py migrate` (auto-injected by Railpack on first deploy)
  3. Start Gunicorn via `railway.toml` start command

  > **Edge case — Railpack does NOT detect uv.lock:** if the build log shows `pip install` instead of `uv sync`, Railpack missed the lock file. Add a `nixpacks.toml` or switch to an explicit `railway.toml` `[build]` section with `buildCommand = "uv sync --frozen"`. The Render fallback documented in `infrastructure.md` is the documented escape path.

  > **Edge case — health check timeout during migration:** if the initial `migrate` (auto-run by Railpack) takes >30 seconds, Railway kills the container mid-migration. Symptoms: Railway dashboard shows "Deploy failed" despite a green build. Fix: add `[deploy] startCommand` to `railway.toml` that does NOT include `migrate`, then run migrations manually: `railway run python manage.py migrate` before the next `railway up`.

- [ ] **6.4** Watch deploy logs:
  ```powershell
  railway logs --build   # Railpack build output
  railway logs           # runtime logs (Gunicorn startup)
  ```

- [ ] **6.5** Open the deployed app:
  ```powershell
  railway open
  ```
  Navigate to `<appname>.up.railway.app` — expect Django's default 200 response (or a 404 from `urls.py` if no root URL pattern is set — both are acceptable; a 502 is not).

---

## Phase 7 — Verification

- [ ] **7.1** Django admin reachable: navigate to `<appname>.up.railway.app/admin/` — expect the login page (not a 500).
- [ ] **7.2** Database connectivity: `railway run python manage.py showmigrations` — all migrations should show `[X]`.
- [ ] **7.3** Static files served: navigate to `<appname>.up.railway.app/static/admin/css/base.css` — expect `200 OK`, not a 404. This confirms WhiteNoise is active.
- [ ] **7.4** Confirm `DEBUG=False` is live: navigate to a non-existent URL (e.g. `/does-not-exist`) — expect Django's generic 404 page, NOT a debug traceback with code snippets.
- [ ] **7.5** Check `CONN_MAX_AGE`: `railway logs | grep "database"` — no "too many connections" errors after the first few requests.

---

## Phase 8 — Post-Deploy Housekeeping

- [ ] **8.1** Create a Railway superuser for admin access:
  ```powershell
  railway run python manage.py createsuperuser
  ```
  > **Edge case — interactive prompts in railway run:** if the TTY is not allocated correctly, pass credentials non-interactively: `railway run python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); U.objects.create_superuser('admin','bozowski@gmail.com','<password>')"`.

- [ ] **8.2** Bookmark the Railway dashboard deployment page URL for manual rollback (no CLI rollback exists — per `infrastructure.md` risk register). Document as: Railway dashboard → corobimy project → Deployments → select last good deployment → Rollback.

- [ ] **8.3** Update `AGENTS.md`: change `SQLite in dev, PostgreSQL on Fly.io` to `SQLite in dev, PostgreSQL on Railway` and update CLI commands from `uv run python manage.py ...` (no change needed) to note `railway run python manage.py ...` for production operations.

- [ ] **8.4** (Optional) Set up GitHub Actions auto-deploy on merge — connect the Railway project to the GitHub repo in Railway dashboard → Settings → Source Repo. Deferred: `tech-stack.md` specifies GitHub Actions auto-deploy but it is not blocking the MVP.

---

## Files Modified / Created

| File | Action | Purpose |
|---|---|---|
| `pyproject.toml` | Create | uv project metadata + runtime dependencies |
| `uv.lock` | Create (generated) | Railpack lock file detection |
| `.gitignore` | Create | Prevent secrets/venv/db from being committed |
| `corobimy/settings.py` | Edit | Env-var driven config, Postgres, WhiteNoise |
| `railway.toml` | Create | Explicit Railpack start command + health check |
| `AGENTS.md` | Edit | Update platform reference from Fly.io to Railway |

---

## Rollback SOP (no `railway rollback` CLI command)

1. Open Railway dashboard → corobimy project → Deployments tab
2. Click the last successful deployment
3. Click **Rollback**
4. Time-to-revert: 1–3 minutes
5. **DB migrations do NOT roll back automatically** — always write backward-compatible migrations before deploying irreversible schema changes

---

## Risk Register References

Risks carried from `context/foundation/infrastructure.md` and how this plan mitigates them:

| Risk | Mitigation in this plan |
|---|---|
| Railpack beta regression | `railway.toml` pins explicit start command; `infrastructure.md` documents Render as migration path |
| Mid-migration container kill | Phase 6.3 edge case: decouple `migrate` from start command if needed |
| Postgres connection saturation | Phase 2.6: `conn_max_age=60` set via `dj_database_url.config` |
| No CLI rollback | Phase 8.2: dashboard URL bookmarked, manual SOP documented |
| Railway `${{...}}` vendor lock-in | Phase 5.2 note: keep migration checklist of Railway-specific variable references |
| SECRET_KEY committed | Phase 3.1: `.gitignore` + Phase 2.2: env-var driven |

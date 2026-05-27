# Repository Guidelines

**corobimy** is a Django 6 web app for discovering Kraków attractions. Stack: Python + Django, `uv` package manager, SQLite in dev, PostgreSQL on Railway, GitHub Actions CI (auto-deploy-on-merge planned). Live at `https://web-production-1188c.up.railway.app`.

## Hard Rules

- Never commit `SECRET_KEY` from `corobimy/settings.py` to any non-local environment; override via a `DJANGO_SECRET_KEY` env var before any deploy.
- Do not place feature code inside `corobimy/` — that package is project config only (settings, urls, wsgi, asgi). Create new Django apps at repo root with `uv run python manage.py startapp <name>`, then register the app's `AppConfig` in `INSTALLED_APPS` in `@corobimy/settings.py`.
- `context/archive/` is immutable — do not write there. New work belongs in `context/changes/`.

## Project Structure

- `corobimy/` — Django project config package; not a feature module.
- `context/foundation/` — PRD, tech-stack, shape notes; read-only design inputs.
- `manage.py` —  always invoke via `uv run`.
- `.venv/` — managed by `uv`; do not edit manually.

New feature apps (e.g., `attractions/`, `accounts/`) land as sibling directories next to `manage.py`.

## Build, Test, and Development Commands

- `uv run python manage.py runserver` — dev server on port 8000
- `uv run python manage.py migrate` — run after every model change or git pull that includes a new migration
- `uv run python manage.py makemigrations` — commit the generated file in the same PR as the model change
- `uv run python manage.py test` — run test suite (no tests yet)
- `uv run python manage.py createsuperuser` — create admin account locally (dev)
- `railway run uv run python manage.py ...` — run management commands against Railway Postgres (note: `postgres.railway.internal` is only reachable inside Railway's private network; use `railway ssh --service web` for interactive commands or attach a public Postgres URL for local access)
- `railway up --detach` — deploy from local to the `web` service on Railway
- `railway logs` — tail runtime logs; `--build` for build logs

## Domain Model

- Core category tags: `family`, `couples`, `sport`, `culture` — the only valid values; do not add or rename categories without updating `@context/foundation/prd.md`. 
- Browse-first auth: anonymous users may read the feed freely; saving an attraction requires authentication. 
- Seed data is required so the feed is non-empty before the AI categorization pipeline is stable. See `@context/foundation/prd.md` for acceptance criteria and the must-have/nice-to-have split.

## Commit Conventions

Existing commits use lowercase imperative phrases without a prefix scheme (e.g. `bootstraping`, `prd.md and tech-stack selection`). Match this style; no Conventional Commits prefixes are in use yet.

## Coding Style

- Python only; no frontend JS framework in MVP scope.
- Settings overrides via env vars — no separate settings files (`settings/prod.py` pattern is not in use).
- Auth: Django's built-in `django.contrib.auth`; no custom authentication backend.

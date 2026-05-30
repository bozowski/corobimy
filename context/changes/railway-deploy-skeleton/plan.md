# Railway Deploy Skeleton — Implementation Plan

## Overview

Close the three remaining gaps in F-01: a `/health/` endpoint for Railway's health check, a `LOGGING` config surfacing Django WARNING+ to the log stream, and updating `railway.toml` to point the health check at `/health/` instead of `/admin/login/`. The app is already live at `https://web-production-1188c.up.railway.app`; all changes are additive.

## Current State Analysis

What's already done (from git history and codebase inspection):

- Django 6.0.5 running on Railway with Gunicorn, 2 workers
- PostgreSQL wired via `DATABASE_URL` env var; `CONN_MAX_AGE=60` set in `settings.py:79`
- `collectstatic` + `migrate` coupled in `railway.toml` start command (kept — acceptable at MVP scale)
- WhiteNoise serving static files (`settings.py:44`, `settings.py:120–124`)
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS` all env-var driven (`settings.py:24–28`)

Three gaps remain:

- **`/health/` endpoint absent** — `railway.toml:3` health check path is `/admin/login/`; that route requires auth and is not a real health signal
- **No `LOGGING` config** — `settings.py` has no `LOGGING` dict; Django's default logging silences WARNING/ERROR in production
- **`railway.toml` healthcheckPath stale** — still `/admin/login/`; must move to `/health/` once the endpoint exists

### Key Discoveries

- `corobimy/urls.py:20–22` — only `admin/` wired; no root or health path
- `corobimy/settings.py` — no `LOGGING` key anywhere in the file (125 lines)
- `railway.toml:3` — `healthcheckPath = "/admin/login/"` — must be updated in the same commit as the view to avoid a health-check gap

## Desired End State

After this plan:

- `GET /health/` returns `HTTP 200` with body `{"status": "ok"}` and no auth required, both locally and on Railway
- `railway.toml` `healthcheckPath` is `/health/`; Railway's health check dashboard shows green via the real endpoint
- `railway logs` surfaces Django WARNING and ERROR entries (e.g., a misconfig or 500) without noise from DEBUG-level SQL traces
- `python manage.py check` passes locally with no errors

Verification command: `curl https://web-production-1188c.up.railway.app/health/` → `{"status": "ok"}`, HTTP 200.

## What We're NOT Doing

- No DB ping in the health check — shallow 200 is sufficient at this stage; DB failures appear in request logs
- No structured JSON log formatting — Django default text format to stdout is readable via `railway logs`
- No CI/CD pipeline — deferred per roadmap
- No change to the migration coupling in the start command — risk is negligible with only Django's built-in migrations
- No HTTPS/TLS settings — Railway terminates TLS at the edge; Django doesn't need to configure it

## Implementation Approach

Two phases, one commit each. Phase 1 adds the view and updates `railway.toml` atomically (they must ship together — updating the health path before the endpoint exists would cause Railway health checks to fail). Phase 2 adds `LOGGING` independently with no deploy risk.

## Phase 1: Health check endpoint

### Overview

Create the `/health/` view, wire it into the URL conf, and update `railway.toml` to point Railway's health check at it.

### Changes Required

#### 1. Health view

**File**: `corobimy/views.py` (new file)

**Intent**: Provide a project-level view for the `/health/` endpoint. Keeping it in the project package (not an app) is correct — this is infrastructure, not a feature.

**Contract**: One public function `health(request)` returning `JsonResponse({'status': 'ok'})`. No auth decorator. No DB access.

#### 2. URL wiring

**File**: `corobimy/urls.py`

**Intent**: Register the health view at `/health/` so Railway's health check and any monitoring tool can reach it without auth.

**Contract**: Add `from corobimy import views` import and `path('health/', views.health, name='health')` to `urlpatterns`. Existing `admin/` path is unchanged.

#### 3. Railway health check path

**File**: `railway.toml`

**Intent**: Tell Railway to use the real health endpoint instead of the admin login page, which requires auth and is not a reliable liveness signal.

**Contract**: Change `healthcheckPath` from `"/admin/login/"` to `"/health/"`. No other lines change.

#### 4. Health endpoint test

**File**: `corobimy/tests.py` (new file)

**Intent**: Guard `/health/` against silent regressions caused by future middleware additions or URL restructuring — Railway's liveness signal depends on this endpoint.

**Contract**: One `TestCase` subclass with one method that GETs `/health/` via `self.client` and asserts `status_code == 200` and `response.json() == {'status': 'ok'}`.

### Success Criteria

#### Automated Verification

- Django system check passes: `python manage.py check`
- Health endpoint reachable locally: `python manage.py runserver` then `curl http://localhost:8000/health/` returns `{"status": "ok"}` with HTTP 200
- No import errors: `python manage.py shell -c "from corobimy.views import health; print('ok')"`
- Health check test passes: `python manage.py test corobimy`

#### Manual Verification

- After `railway up --detach`, `curl https://web-production-1188c.up.railway.app/health/` returns `{"status": "ok"}` with HTTP 200
- Railway dashboard → corobimy project → health check shows green (no longer hitting `/admin/login/`)
- Visiting `/health/` while logged out returns 200 (confirm no auth required)



**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to Phase 2. Phase blocks use plain bullets — the corresponding `- [ ]` checkboxes for these items live in the `## Progress` section at the bottom of the plan.

---

## Phase 2: Error logging config

### Overview

Add a `LOGGING` dict to `settings.py` that routes Django WARNING and above to stdout via a console handler. No new dependencies required — Python's `logging` stdlib handles this.

### Changes Required

#### 1. LOGGING config

**File**: `corobimy/settings.py`

**Intent**: Surface Django WARNING and ERROR entries in `railway logs` so silent failures (misconfigured env vars, 500s, auth errors) are visible without enabling DEBUG-level SQL noise.

**Contract**: Append a `LOGGING` dict at the end of `settings.py` with:

- One handler: `console` — `logging.StreamHandler` writing to `sys.stdout`
- One logger entry: `django` — level `WARNING`, propagate `False`, handler `console`
- `disable_existing_loggers: False` — leaves third-party library loggers untouched

> **S-01 note**: This config covers only `django.*` loggers. When S-01 adds app code that uses `logging.getLogger(__name__)`, add `'root': {'handlers': ['console'], 'level': 'WARNING'}` to this dict so app-level errors appear in `railway logs`.

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

### Success Criteria

#### Automated Verification

- Django system check passes: `python manage.py check`
- Logging config loads without ImportError: `python manage.py shell -c "import logging; l = logging.getLogger('django'); l.warning('test'); print('ok')"`

#### Manual Verification

- After `railway up --detach`, trigger a 404 or intentional warning: `railway logs` shows a WARNING or ERROR line from the `django` logger (e.g., navigate to `/does-not-exist` and observe `Not Found: /does-not-exist` in the log stream)
- No DEBUG-level SQL traces in `railway logs` (confirm noise floor is clean)

**Implementation Note**: After completing this phase and all automated verification passes, pause for manual confirmation that logs are visible in `railway logs` before marking F-01 complete.

---

## Testing Strategy

### Automated

- `python manage.py check` — covers import errors and config issues across both phases
- `curl http://localhost:8000/health/` — validates the endpoint contract locally

### Manual Testing Steps

1. Run `python manage.py runserver`, visit `http://localhost:8000/health/` — expect `{"status": "ok"}`
2. After deploy: `curl https://web-production-1188c.up.railway.app/health/` — expect `{"status": "ok"}` with HTTP 200
3. Railway dashboard health check shows green
4. `railway logs` shows a WARNING entry after a 404 visit

## References

- Infrastructure platform decision: `context/foundation/infrastructure.md`
- Roadmap F-01: `context/foundation/roadmap.md` (lines 61–72)
- Prior deployment work: `context/changes/deployment/deployment-plan.md`
- Live app: `https://web-production-1188c.up.railway.app`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Health check endpoint

#### Automated

- [x] 1.1 Django system check passes: `python manage.py check`
- [x] 1.2 Health endpoint reachable locally: `curl http://localhost:8000/health/` returns `{"status": "ok"}` HTTP 200
- [x] 1.3 No import errors: `python manage.py shell -c "from corobimy.views import health; print('ok')"`
- [x] 1.4 Health check test passes: `python manage.py test corobimy`

#### Manual

- [ ] 1.5 After deploy, `curl https://web-production-1188c.up.railway.app/health/` returns `{"status": "ok"}` HTTP 200
- [ ] 1.6 Railway dashboard health check shows green
- [ ] 1.7 `/health/` returns 200 while logged out (no auth required)

### Phase 2: Error logging config

#### Automated

- [ ] 2.1 Django system check passes: `python manage.py check`
- [ ] 2.2 Logging config loads without ImportError: `python manage.py shell -c "import logging; l = logging.getLogger('django'); l.warning('test'); print('ok')"`

#### Manual

- [ ] 2.3 After deploy, `railway logs` shows a WARNING entry after a 404 visit
- [ ] 2.4 No DEBUG-level SQL traces visible in `railway logs`

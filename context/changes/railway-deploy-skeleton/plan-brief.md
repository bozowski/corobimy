# Railway Deploy Skeleton — Plan Brief

> Full plan: `context/changes/railway-deploy-skeleton/plan.md`

## What & Why

Close the three remaining gaps in F-01 — the `/health/` endpoint, Django error logging, and the `railway.toml` health check path — so the foundation slice is verifiably done. The app is already live on Railway; this is the last ~30 lines of code between "deployed" and "observable and correctly health-checked."

## Starting Point

Django 6.0.5 running on Railway with Postgres, WhiteNoise, and gunicorn. All environment variables are wired. The one missing piece: `railway.toml` health check still points to `/admin/login/` (an auth-gated page), and `settings.py` has no `LOGGING` config, so errors are silent in `railway logs`.

## Desired End State

`GET /health/` returns `{"status": "ok"}` with HTTP 200, no auth required, both locally and on Railway. Railway's health check dashboard goes green via the real endpoint. `railway logs` surfaces Django WARNING and ERROR entries on demand — a 404 or misconfiguration is no longer silent.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Health check depth | Shallow — HTTP 200 only | DB failures appear in request logs; a DB ping adds flap risk to the health check cycle | Plan |
| Health response body | JSON `{"status": "ok"}` | Standard format, works with any future monitoring tool | Plan |
| Log levels | WARNING + ERROR (django logger) | Surfaces warnings that predict errors during early dev without SQL-level noise | Plan |
| Log destination | stdout via StreamHandler | Railway captures stdout in `railway logs`; no extra tooling needed | Plan |
| Migration coupling | Keep coupled in start command | Only Django built-in migrations exist; decoupling adds manual steps for no gain at this scale | Plan |

## Scope

**In scope:**
- `corobimy/views.py` — new file with `health` view
- `corobimy/urls.py` — add `/health/` path
- `railway.toml` — update `healthcheckPath` to `/health/`
- `corobimy/settings.py` — append `LOGGING` dict (WARNING+ to stdout)

**Out of scope:**
- DB connectivity check in `/health/`
- Structured JSON log format
- CI/CD pipeline
- HTTPS/TLS Django settings (Railway terminates TLS at the edge)

## Architecture / Approach

Two phases, one commit each. Phase 1 ships the view + railway.toml atomically (updating the health path before the endpoint exists would cause Railway to report unhealthy). Phase 2 adds `LOGGING` independently — zero deploy risk, no Railway restart required.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Health check endpoint | `/health/` view, URL wiring, railway.toml path update | Must ship view + config together — partial deploy leaves health check broken |
| 2. Error logging config | Django WARNING+ surfaced in `railway logs` | None — purely additive settings change |

**Prerequisites:** App live on Railway with Postgres wired (already done).
**Estimated effort:** ~1 session, 2 commits, ~30 lines of code.

## Open Risks & Assumptions

- Railway health check TTL: after updating `healthcheckPath`, Railway may take 1–2 minutes to re-evaluate. Brief "unhealthy" state during the redeploy is expected and not a sign of failure.
- `corobimy/views.py` doesn't exist yet — the plan creates it as a new file; no existing code is displaced.

## Success Criteria (Summary)

- `curl https://web-production-1188c.up.railway.app/health/` returns `{"status": "ok"}` HTTP 200
- Railway dashboard health check shows green
- `railway logs` shows a WARNING entry after visiting a non-existent URL

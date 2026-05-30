---
change_id: railway-deploy-skeleton
title: Wire Railway deployment skeleton with Postgres, health check, and error logging
status: implementing
created: 2026-05-30
updated: 2026-05-30
archived_at: null
---

## Notes

F-01 from roadmap. Outcome: Django app running on Railway with PostgreSQL connected (DATABASE_URL, SECRET_KEY, ALLOWED_HOSTS, CONN_MAX_AGE=60), collectstatic passing, a `/health/` endpoint responding HTTP 200, and error-level logs surfaced to the Railway log stream via Django `LOGGING` config.

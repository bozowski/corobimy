---
project: corobimy
researched_at: "2026-05-26"
recommended_platform: Railway
runner_up: Render
context_type: mvp
tech_stack:
  language: Python
  framework: Django
  runtime: Python 3.13
  database: PostgreSQL
  package_manager: uv
---

## Recommendation

**Deploy on Railway.**

Railway is the lowest-cost persistent-process PaaS that natively supports Django + uv, co-locates a managed PostgreSQL database in the same Amsterdam project, and ships a Claude Code plugin for agent-driven operations. At $5–8/month it is the only option in the candidate pool that fits within the MVP cost priority stated in the interview, and its Railpack build toolchain is the only one that detects `uv.lock` automatically without requiring a hand-authored Dockerfile. The single-region EU requirement (Amsterdam) is met, Postgres connection details are injected as environment variables by default, and all routine operations — deploy, logs, variable management — are covered by the `railway` CLI.

## Platform Comparison

### Scoring Matrix

| Platform | CLI-first | Managed/Serverless | Agent-readable docs | Stable deploy API | MCP / Integration | Weighted |
|---|---|---|---|---|---|---|
| **Railway** | Partial | Pass | Partial | Pass | Partial | **4.5** |
| **Render** | Partial | Pass | Pass | Partial | Partial | **4.0** |
| **AWS App Runner** | Partial | Pass | Fail | Pass | Pass | **4.0** |
| **Fly.io** | Pass | Pass | Partial | Pass | Partial | **2.5** |
| Netlify | — | — | — | — | — | Dropped (serverless-only) |
| Vercel | — | — | — | — | — | Dropped (serverless-only / JS-primary) |
| Cloudflare Workers | — | — | — | — | — | Dropped (JS/Wasm runtime; Django unsupported) |

Scoring notes per criterion:

**CLI-first**: Railway's `railway` CLI covers deploy, logs, variables, and auth. Rollback is dashboard-only (no `railway rollback` command) → Partial. Render's CLI is GA but also lacks a rollback command → Partial. AWS CLI is comprehensive but VPC Connector setup requires console → Partial. Fly.io's `flyctl` covers every operation including rollback via re-deploy → Pass.

**Managed/Serverless**: All four surviving candidates are fully managed PaaS — no EC2/OS patching, no networking configuration — so all score Pass.

**Agent-readable docs**: Render publishes `llms.txt`, `llms-full.txt`, and per-page markdown → Pass. Railway docs are GitHub-hosted markdown but no `llms.txt` → Partial. Fly.io docs are GitHub markdown, no `llms.txt` → Partial. AWS docs are JS-rendered HTML, no `llms.txt`; the AWS MCP Server partially compensates → Fail.

**Stable deploy API**: Railway `railway up --detach` returns a structured exit code and supports `RAILWAY_TOKEN` for CI → Pass. Fly.io `fly deploy` is deterministic with image rollback → Pass. AWS `aws apprunner update-service` is structured JSON → Pass. Render's deploy API requires REST calls with manual `autoDeploy` flag management and no CLI rollback → Partial.

**MCP / Integration**: Railway ships an active-development MCP server and a Claude Code plugin (`use-railway` skill) → Partial. Render's infrastructure MCP server is available but cannot trigger deploys → Partial. Fly.io's `fly mcp server` is experimental → Partial. AWS MCP Server is GA (May 6, 2026), covers App Runner + RDS + CloudWatch → Pass.

**Interview weight adjustments (applied to weighted score)**:
- Minimize cost (Q2): Fly.io −2 (Postgres alone is $38/month), AWS −1 ($26–35/month), Render −0.5 ($14/month), Railway 0 ($5–8/month).
- Co-location preferred (Q5): Railway +1 (Postgres in same project, Amsterdam), Render +1 (Postgres in same region, Frankfurt), AWS +0.5 (RDS via VPC Connector, added complexity), Fly.io +0.5 (Managed Postgres available but expensive).
- AWS familiarity (Q3): AWS +1 tie-breaker.

### Shortlisted Platforms

#### 1. Railway (Recommended)

Railway wins on cost, native stack compatibility, and agent integration. At $5–8/month (Hobby plan $5 flat + usage), it is 2× cheaper than Render and 5× cheaper than Fly.io for the same persistent Django + Postgres setup. Railpack (beta, March 2026) detects `uv.lock` automatically and generates an idiomatic Django start command without a hand-authored Dockerfile. The Claude Code `use-railway` plugin installs a `railway` skill directly into the agent workflow. Co-located Postgres runs in the same Railway project in EU West Metal (Amsterdam) with connection details automatically injected as environment variables.

#### 2. Render

Render scores second on documentation quality — it publishes `llms.txt` and `llms-full.txt`, making it the most agent-readable option in the pool. Native uv support is GA (June 12, 2025), and the CLI is fully GA (December 2024). Estimated cost is $14/month (Starter web service $7 + Basic Postgres $7) in Frankfurt. The gap vs. Railway is the missing CLI rollback (requires REST API) and roughly double the monthly cost. Render is the natural migration target if Railway's Railpack beta causes build friction.

#### 3. AWS App Runner + RDS

AWS earns third place primarily on familiarity (you have hands-on AWS experience) and on MCP maturity — the AWS MCP Server reached GA on May 6, 2026, covering App Runner, RDS, ECR, and CloudWatch from a single structured tool. Estimated cost is $26–35/month (App Runner + RDS db.t4g.micro in eu-west-1). The VPC Connector setup for private RDS connectivity is a one-time 15-minute task, well-documented. AWS is the natural path if the app outgrows Railway's single-AZ Amsterdam deployment or if GDPR audit requirements demand a more auditable control plane.

## Anti-Bias Cross-Check: Railway

### Devil's Advocate — Weaknesses

1. **No CLI rollback.** There is no `railway rollback` command. Rolling back a broken deploy requires either clicking the Railway dashboard or knowing the specific deployment ID to pass to `railway redeploy`. An agent cannot execute a clean rollback autonomously; a human must be available.
2. **Railpack is beta.** The build toolchain providing native uv support launched March 4, 2026, and is still labeled beta. Django + uv has sparse community examples on the platform. A Railpack regression mid-sprint could silently break the build while appearing to succeed.
3. **No managed connection pooling.** Railway Postgres has no built-in PgBouncer. Django's default behavior opens a new connection per worker per restart. Without `CONN_MAX_AGE` configured from day one, connection saturation will occur under moderate load (30+ concurrent users with 10 Gunicorn workers).
4. **Single-AZ EU region only.** EU West Metal (Amsterdam) is one datacenter. There is no multi-AZ failover at Hobby tier. A platform event means total downtime with no automated recovery path.
5. **Startup platform risk.** Railway changed its pricing model in 2023. The MCP server is explicitly marked "a work in progress." A solo developer on a Hobby plan has no SLA guarantee and is fully dependent on Railway's roadmap prioritization.

### Pre-Mortem — How This Could Fail

The team chose Railway for its low cost and apparent Django simplicity. Six months later, Railpack ships a breaking change to its Django auto-detection and the auto-generated start command now points to the wrong WSGI module. The deployment returns a green build indicator but a silent 502 to users. `railway logs` surfaces a health check failure with no clear root cause, and inspecting the running container requires Railway's web shell rather than the CLI. Debugging takes hours. Simultaneously, Postgres connections are saturating under 30 concurrent users because `CONN_MAX_AGE` was never set and PgBouncer isn't available. Attempting to roll back, the developer finds there is no `railway rollback` command and must navigate the dashboard from a phone at 11pm — the experience that was supposed to be agent-driven is entirely manual. The Railway MCP server, labeled "a work in progress," cannot trigger deployments. The $8/month saving over Render has consumed an entire weekend and eroded trust in the stack.

### Unknown Unknowns

- **Railpack injects `python manage.py migrate` into the start command.** If a migration takes longer than Railway's health check timeout (typically 30–60 seconds for a cold start), the container is killed mid-migration, potentially leaving the database in a half-migrated state. Decouple migrations from the start command for any non-trivial schema change.
- **Railway's control plane is US-hosted** even when compute runs in EU West Metal. User data lives in Amsterdam; deploy logs, secrets management, and dashboard operations transit US infrastructure. For a Kraków tourist app this is likely acceptable, but document it if GDPR processing agreements are ever audited.
- **`${{Postgres.PGHOST}}` variable syntax is Railway-proprietary.** Every service config reference must be rewritten when migrating to another platform. Keep a migration checklist of all Railway-specific variable references from day one.
- **Silent service restarts on OOM or platform events** will clear any in-process Django state (local-memory cache, open file handles). Safe if all state is in Postgres; dangerous if any per-process memory is assumed to persist between requests.

## Operational Story

- **Preview deploys**: Railway supports per-environment deployments (Production + staging environments configurable in the dashboard). Branch-based PR previews require manual environment setup — not automatic by default. Protection requires a separate Railway environment with its own secrets, not Cloudflare Access.
- **Secrets**: Environment variables live in the Railway dashboard → Service → Variables. Set via CLI with `railway variables set KEY=value` or `railway variables set KEY=value --environment production`. Rotation requires updating the variable value; Railway auto-redeploys on secret change (configurable). Secrets are scoped per service and environment — never in `.env` files committed to the repo.
- **Rollback**: Navigate to Railway dashboard → Project → Deployments → select the last successful deployment → click Rollback. Typical time-to-revert: 1–3 minutes. DB migrations do NOT roll back automatically — always write backward-compatible migrations before deploying irreversible schema changes.
- **Approval**: Deploy (`railway up`), variable management (`railway variables set`), log access (`railway logs`), and service restart can be performed by the agent unattended via CLI. Destructive actions — deleting a service, dropping the database, rotating the primary `SECRET_KEY` — are human-only operations via the dashboard.
- **Logs**: `railway logs` streams live runtime logs to the terminal. `railway logs --build` streams the Railpack build log. `railway logs -n 100` returns the last 100 lines. Structured log filtering is not supported in the CLI — use the dashboard for keyword filtering or level filtering.

## Risk Register

| Risk | Source | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| No CLI rollback — agent blocked on broken deploy | Devil's advocate | M | H | Bookmark the Railway dashboard deployment page; document manual rollback SOP; `railway redeploy <deployment-id>` is a partial CLI path |
| Railpack beta regression breaks uv/Django detection | Devil's advocate | L | H | Test build on day 1 before writing app code; keep a Dockerfile fallback ready; Render is the documented migration path |
| Postgres connection saturation under moderate load | Devil's advocate | M | M | Set `CONN_MAX_AGE=60` in `DATABASES` settings before first production deploy; monitor connection count via `railway logs` |
| Single-AZ EU region — no failover path | Devil's advocate | L | H | Accept for MVP; migrate to Railway Pro with HA Postgres or to Render before entering growth phase |
| Railway pricing or platform change risk | Devil's advocate | L | M | Keep `railway.toml` + Dockerfile export ready; document a one-day Render migration runbook |
| Railpack migration injection causes mid-migration container kill | Unknown unknowns | L | H | Decouple non-trivial migrations: run `railway run python manage.py migrate` manually before `railway up` for migrations touching large tables |
| GDPR control plane audit — Railway secrets transit US infrastructure | Unknown unknowns | L | M | Document the data flow boundary; operational data (secrets, logs) vs. personal data (Postgres in Amsterdam) distinction is defensible but must be explicit |
| Railway `${{...}}` variable syntax vendor lock-in | Unknown unknowns | L | L | Maintain a migration checklist of all Railway-specific variable references from day one |

## Getting Started

1. **Install the Railway CLI** (Windows PowerShell): `npm i -g @railway/cli` or via the installer at `install.railway.app`.
2. **Authenticate**: `railway login` — opens a browser for OAuth; `railway login --browserless` for headless environments.
3. **Initialise the project**: in the repo root, run `railway init` and select "Create a new project". Railway links the local directory to the project.
4. **Add Postgres**: in the Railway dashboard, open the project, click "Add Service" → "Database" → "PostgreSQL". Railway creates a Postgres service in EU West Metal (Amsterdam) and makes connection variables available as `${{Postgres.DATABASE_URL}}`, `${{Postgres.PGHOST}}`, etc.
5. **Configure environment variables** in the Railway dashboard → Service → Variables (or via CLI):
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   - `SECRET_KEY` = `<generate with: python -c "import secrets; print(secrets.token_hex(50))">`
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `<appname>.up.railway.app`
6. **Deploy**: `railway up --detach` — Railpack detects `uv.lock` and Django, installs dependencies with `uv sync`, and starts Gunicorn. First deploy auto-runs `python manage.py migrate`.
7. **Install the Claude Code plugin** (optional but recommended): `/plugin marketplace add railwayapp/railway-skills` then `/plugin install railway@railway-skills`. Installs a `use-railway` skill for agent-driven deployment and troubleshooting.

## Out of Scope

The following were not evaluated in this research:
- Docker image configuration and multi-stage Dockerfile optimization
- CI/CD pipeline setup (GitHub Actions auto-deploy on merge)
- Production-scale architecture (multi-region, HA, disaster recovery)
- Static file CDN configuration (WhiteNoise vs. external object storage)

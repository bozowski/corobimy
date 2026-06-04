---
project: corobimy
version: 1
status: draft
created: 2026-05-29
updated: 2026-05-29
prd_version: 1
main_goal: speed
top_blocker: capacity
---

# Roadmap: corobimy

> Derived from `context/foundation/prd.md` (v1) + auto-researched codebase baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Vision recap

People planning a free day in Kraków don't know what attractions are available or which ones suit them. Browsing TripAdvisor, Google Maps, and local sites is scattered and produces no personalized signal. This app closes that gap: it aggregates local Kraków attractions and lets users filter by preference category (family / couples / sport / culture), producing a personalized shortlist from a single interaction. The core bet is that AI-assisted categorization makes this cheap enough to run on demand, per user request.

## North star

**S-02: user can save an attraction (browse-first auth gate)**

The north star — the smallest end-to-end slice whose delivery proves the product works as described — is the full browse → filter → save → auth gate flow: an anonymous user browses the curated feed, attempts to save an attraction, completes email/password registration, and has the save persisted without losing the selected item mid-flow.

> "North star" here means: the one slice whose successful delivery would prove the product does what it claims. It is placed as early as Prerequisites allow because everything else only matters if this works.

## At a glance

| ID   | Change ID                 | Outcome (user can …)                                                                  | Prerequisites | PRD refs                       | Status   |
|------|---------------------------|---------------------------------------------------------------------------------------|---------------|--------------------------------|----------|
| F-01 | railway-deploy-skeleton   | (foundation) Django live on Railway, Postgres wired, /health/ endpoint, errors logged | —             | PRD §NFRs, PRD §Access Control | done     |
| S-01 | attraction-browse-feed    | browse and filter Kraków attractions without signing in                               | F-01          | FR-003, FR-004                 | in-progress |
| S-02 | browse-first-save         | save an attraction; if anonymous, complete auth gate without losing the selection     | S-01          | FR-001, FR-002, FR-005, US-01  | proposed |
| S-03 | operator-content-refresh  | (operator) manually trigger a refresh of Kraków attraction listings                   | S-01          | FR-009                         | blocked  |

## Streams

Navigation aid — groups items that share a Prerequisites chain. Canonical ordering still lives in the dependency graph below; this table is the proposed reading order across parallel tracks.

| Stream | Theme             | Chain                        | Note                                                                    |
|--------|-------------------|------------------------------|-------------------------------------------------------------------------|
| A      | Browse & save     | `F-01` → `S-01` → `S-02`    | Required FR path to the north star; F-01 is plannable now.              |
| B      | Content pipeline  | `S-01` → `S-03`             | Parallel with S-02 after S-01 lands; blocked by content-source decision.|

## Baseline

What's already in place in the codebase as of 2026-05-29 (auto-researched + user-confirmed). Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend:** absent — no templates, no static assets; WhiteNoise middleware configured but no files served
- **Backend / API:** partial — Django 6.0.5 in place (`corobimy/urls.py`), only admin route wired, zero custom views
- **Data:** partial — Django ORM + psycopg driver configured (`settings.py:76`), no models or migrations
- **Auth:** partial — Django session/auth middleware in place (`settings.py:45-48`), no custom views or `@login_required`
- **Deploy / infra:** partial — `railway.toml` present (Railpack builder, gunicorn), no Dockerfile, no CI/CD
- **Observability:** absent — no custom logging config, health check piggybacking on `/admin/login/`, no error tracking

## Foundations

### F-01: Deploy skeleton + minimal observability

- **Outcome:** (foundation) Django app running on Railway with PostgreSQL connected (DATABASE_URL, SECRET_KEY, ALLOWED_HOSTS, CONN_MAX_AGE=60), collectstatic passing, a `/health/` endpoint responding HTTP 200, and error-level logs surfaced to the Railway log stream via Django `LOGGING` config.
- **Change ID:** railway-deploy-skeleton
- **PRD refs:** PRD §Non-Functional Requirements (2-second load time requires working Postgres; privacy NFR requires correct env isolation), PRD §Access Control (browse-first pattern requires session storage in Postgres)
- **Unlocks:** S-01, S-02, S-03 — all slices are deployable and observable in production. The `/health/` endpoint provides verification infrastructure that S-01's 2-second-load acceptance criterion depends on; error logging surfaces silent failures in the auth and data flows before S-02 is exercised.
- **Prerequisites:** —
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** Railpack (beta, launched March 2026) auto-detects `uv.lock` + Django 6.0.5 without a hand-authored Dockerfile — verify on first `railway up`; infrastructure.md documents a Dockerfile fallback if detection fails. Owner: dev. Block: no.
- **Risk:** Sequenced first because every slice needs Postgres accessible and the app deployed to be verified against real infrastructure. Main risk: migration timing vs. Railway health-check timeout (infrastructure.md §Unknown Unknowns) — decouple non-trivial migrations from the gunicorn start command.
- **Status:** done

## Slices

### S-01: Attraction browse feed

- **Outcome:** user can open the app, see a list of seeded Kraków attractions, and optionally filter by preference category (family / couples / sport / culture) — no sign-in required.
- **Change ID:** attraction-browse-feed
- **PRD refs:** FR-003, FR-004
- **Prerequisites:** F-01
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - Which persona (tourist or local) should the browse feed's default ordering and UX tone favor on day 1? — Owner: user. Block: no (PRD marks this non-blocking; both personas see the same feed, but copy and default sort order differ).
- **Risk:** Sequenced before auth because the browse-first pattern (FR-004 Socrates note) lets anonymous users browse freely — building browse first means S-02 adds auth on top of a working feed rather than redesigning it. Main risk: seed data quality — thin or miscategorized initial corpus produces empty filtered states that make the app feel broken before real users arrive.
- **Status:** in-progress

### S-02: Browse-first save (auth gate)

- **Outcome:** user can save an attraction; if anonymous, they are prompted to sign up or sign in; after completing email/password auth, the save action completes without losing the selected attraction, and the saved attraction is persisted to their account.
- **Change ID:** browse-first-save
- **PRD refs:** FR-001, FR-002, FR-005, US-01
- **Prerequisites:** S-01
- **Parallel with:** S-03
- **Blockers:** —
- **Unknowns:**
  - How should the post-auth redirect preserve the pending save — session-based pre-auth buffer, URL parameter, or client-side state? — Owner: dev. Block: no (implementation decision for /10x-plan to resolve).
- **Risk:** This is the north star slice — US-01 acceptance criteria complete here. The riskiest criterion is "save completes without losing the selected attraction" across the auth redirect boundary; browse-first patterns most commonly break at that hand-off.
- **Status:** proposed

### S-03: Operator attraction refresh

- **Outcome:** the operator can manually trigger a refresh of Kraków attraction listings from local websites, updating the corpus that users browse in the app.
- **Change ID:** operator-content-refresh
- **PRD refs:** FR-009
- **Prerequisites:** S-01
- **Parallel with:** S-02
- **Blockers:** —
- **Unknowns:**
  - What is the content acquisition approach? Which local Kraków websites are sources, how should their content be scraped, and how should attractions be categorized (AI-assisted scraping, curated manual entry, or a hybrid)? — Owner: user. Block: yes.
- **Risk:** Sequenced after S-01 because S-01 establishes the Attraction model and initial corpus that the refresh mechanism updates. Blocked by the content-source decision — the implementation diverges significantly depending on whether this is a Django management command, an admin action, or a webhook, and that choice depends on which sites are targeted and how their content is structured.
- **Status:** blocked

## Backlog Handoff

| Roadmap ID | Change ID                | Suggested issue title                               | Ready for `/10x-plan` | Notes |
|------------|--------------------------|-----------------------------------------------------|-----------------------|-------|
| F-01       | railway-deploy-skeleton  | Wire Railway + Postgres, /health/ endpoint, logging | —                     | Done — archived via `/10x-archive` |
| S-01       | attraction-browse-feed   | Browse and filter Kraków attractions (anonymous)    | yes                   | In progress — `/10x-plan attraction-browse-feed` |
| S-02       | browse-first-save        | Save attraction with browse-first auth gate         | no                    | Depends on S-01 |
| S-03       | operator-content-refresh | Operator manual attraction data refresh             | no                    | Blocked — resolve content acquisition Unknown first |

## Open Roadmap Questions

1. **Dual-persona tension** — Tourist vs. local first flows differ significantly (tourists want "highlight reel fast"; locals want "what's new near me"). Which persona should day-1 UX copy and feed ordering favor? — Owner: user. Block: S-01 (non-blocking per PRD, but day-1 UX tone and default sort depend on the answer).

## Parked

- **Attraction rejection / dismiss (FR-006)** — Why parked: demoted to nice-to-have in PRD; requires per-user dismissal state and a meaningful data model addition; deferred to v2.
- **Free-text keyword search (FR-007)** — Why parked: demoted to nice-to-have in PRD.
- **Saved attractions history view (FR-008)** — Why parked: demoted to nice-to-have in PRD; most valuable for returning locals, low value for short-trip tourists.
- **Automated content refresh (FR-009 automation)** — Why parked: PRD §Non-Goals; automated scheduling is a v2 capability.
- **Native mobile app** — Why parked: PRD §Non-Goals; web-only for MVP.
- **Behavioral recommendation algorithm** — Why parked: PRD §Non-Goals; explicit preference filter only, no ML-based personalization.
- **Social / sharing features** — Why parked: PRD §Non-Goals; saved attractions are private per user.
- **Multi-city support** — Why parked: PRD §Non-Goals; Kraków only until product fit is validated.

## Done

| ID   | Change ID               | Outcome                                                                               | Completed  |
|------|-------------------------|---------------------------------------------------------------------------------------|------------|
| F-01 | railway-deploy-skeleton | Django live on Railway, Postgres wired, /health/ endpoint, errors logged to stdout    | 2026-05-30 |

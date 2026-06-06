# Test Plan

> Phased test rollout for this project. Strategy is frozen at the top
> (§1–§5); cookbook patterns at the bottom (§6) fill in as phases ship.
> Read before writing any new test.
>
> Refresh: re-run `/10x-test-plan --refresh` when stale (see §8).
>
> Last updated: 2026-06-06 (Phase 1 change opened)

---

## 1. Strategy

Tests follow three non-negotiable principles for this project:

1. **Cost × signal.** The cheapest test that gives a real signal for the
   risk wins. Do not promote to e2e because e2e "feels safer." Do not put a
   vision model on top of a deterministic check that already catches
   the regression.
2. **User concerns are first-class evidence.** Risks anchored in "the
   team is worried about X, and the failure would surface in <area>"
   carry the same weight as PRD lines or hot-spot data.
3. **Risks are scenarios, not code locations.** This plan documents *what
   could fail* and *why we believe it's likely* — drawn from documents,
   interview, and codebase *signal* (churn, structure, test base). It does
   NOT claim to know which line owns the failure. That knowledge is
   produced by `/10x-research` during each rollout phase. If the plan and
   research disagree about where the failure lives, research is the
   ground truth.

Hot-spot scope used for likelihood weighting: `corobimy/`, `attractions/`
(last 30 days; excluding migrations, fixtures, templates, build output).

---

## 2. Risk Map

The top failure scenarios this project must protect against, ordered by
impact × likelihood. Risks are failure scenarios in user / business terms,
not test names. The Source column cites the *evidence that surfaced this
risk* — never a specific file as "where the failure lives" (that is
research's job; see §1 principle #3).

| # | Risk (failure scenario) | Impact | Likelihood | Source (evidence — not anchor) |
|---|-------------------------|--------|------------|-------------------------------|
| 1 | Saved attraction lost at auth redirect: anonymous user clicks save, completes register/login, attraction absent from their account | High | High | Interview Q1, Q4; PRD US-01 AC "save completes without losing the selected attraction"; roadmap S-02 "riskiest criterion: save completes without losing the selected attraction across the auth redirect boundary" |
| 2 | Save endpoint accepts unauthenticated POST server-side: browse-first gate is UI-only; server does not enforce auth independently | High | Medium | Abuse lens (auth surface); PRD §Access Control "saving requires authentication" |
| 3 | Saved attractions leaked across users: missing user-scope filter exposes one user's saved list to another | High | Low | Abuse lens; PRD §NFRs "saved attractions used only to serve that user's own feed; never shared with third parties" |
| 4 | HTMX partial regression: category filter or load-more swap returns wrong template, wrong queryset, or full page instead of partial | Medium | Medium | Interview Q3 ("HTMX partials — every tweak feels uncertain"); hot-spot dir `attractions/` 12 commits/30d |
| 5 | Settings/env misconfiguration silently breaks prod: absent or wrong critical env vars cause session failures without a startup error | High | Medium | Hot-spot dir `corobimy/` 18 commits/30d (settings is the single hottest file, ×8); roadmap S-02 unknown "how should post-auth redirect preserve the pending save — session-based pre-auth buffer?" |
| 6 | Stale or invalid attraction shown to users: closed or moved venue recommended by the app | Medium | Low | PRD §Success Criteria guardrail "no stale listings — trust-destroying failure"; roadmap S-01 risk "thin or miscategorized initial corpus makes the app feel broken" |

### Risk Response Guidance

| Risk | What would prove protection | Must challenge | Context `/10x-research` must ground | Likely cheapest layer | Anti-pattern to avoid |
|------|-----------------------------|----------------|--------------------------------------|-----------------------|-----------------------|
| #1 | After anonymous-save → register → post-login, the selected attraction is present in the new user's saved list | "Auth completed ⟹ save completed" — they are separate actions; test must confirm the save, not just the logged-in state | How the pre-auth buffer stores and retrieves the pending attraction ID across the redirect; where the post-login handler reads and executes it | Django integration test (`follow=True`) | Testing only login success without asserting the save outcome |
| #2 | Anonymous POST to save URL returns 302→login (or 403) and creates zero database rows | "UI only shows the save button to logged-in users — unauthenticated POST can't happen" — server-side enforcement must exist independently of UI | The save URL pattern and which decorator or middleware enforces auth | Django integration test (anonymous `client.post`) | Testing only the authenticated happy path |
| #3 | User A's saves are absent from User B's saves response | "Single-user test passes ⟹ multi-user is fine" — single-user tests cannot catch a missing user-scope filter | How the saves queryset is filtered in the view | Django integration test (two-user isolation) | Testing only that the authenticated user sees their own saves |
| #4 | GET with `HX-Request: true` uses the partial template and returns only matching-category attractions | "View-level test is sufficient" — what matters is the full HTTP round-trip: template selected, queryset filtered | Which template is selected per request type (full vs. HTMX) and how the `is_htmx` flag is evaluated | Django integration test (`HTTP_HX_REQUEST` header) | Testing the view function return value in isolation without issuing the real HTTP request |
| #5 | `/health/` returns 200 AND a DB write round-trip succeeds; `manage.py check --deploy` passes with expected env vars present | "App starts ⟹ settings are correct" — session-dependent operations can fail silently after a clean startup | Which env vars are load-bearing in settings, what the fallback is when each is absent | `manage.py check` + health integration test that asserts a DB round-trip, not just a 200 | Asserting only the 200 status without verifying Postgres connectivity |
| #6 | Seed fixture loads; all attractions have non-null name + valid category value + non-null description; expected record count present | "Fixture loaded without error ⟹ data is valid" — load success does not validate field content or category constraints | CATEGORY_CHOICES constraint, required fields, expected fixture record count | Django `TestCase` that loads the fixture and asserts field constraints | Testing only that `loaddata` exits cleanly |

---

## 3. Phased Rollout

Each row is a discrete rollout phase that will open its own change folder
via `/10x-new`. Status moves left-to-right through the values below; the
orchestrator updates Status and Change-folder as artifacts appear on disk.

| # | Phase name | Goal (one line) | Risks covered | Test types | Status | Change folder |
|---|------------|-----------------|---------------|------------|--------|---------------|
| 1 | S-02 critical path | Prove save persists across auth redirect; auth gate enforced server-side; user-scope isolation on saves | #1, #2, #3 | Django integration | change opened | context/changes/testing-s02-critical-path/ |
| 2 | HTMX regression guard | Audit S-01 HTMX test completeness; add edge cases; extend with S-02-introduced partials when S-02 ships | #4 | Django integration | not started | — |
| 3 | Env & data guards | Prove critical settings fail loudly; seed data quality assertions | #5, #6 | Django integration + `manage.py check` | not started | — |
| 4 | Quality gates | Name the CI gate floor (lint + typecheck + unit/integration on merge) | cross-cutting | Gate definition | not started | — |

**Status vocabulary** (parser literals — do not rename):

| Value | Meaning |
|---|---|
| `not started` | No change folder for this rollout phase yet. |
| `change opened` | `context/changes/<id>/change.md` exists; research not done. |
| `researched` | `research.md` exists in the change folder. |
| `planned` | `plan.md` exists with a `## Progress` section. |
| `implementing` | Progress section has at least one `[x]` and at least one `[ ]`. |
| `complete` | Progress section is fully `[x]`. |

---

## 4. Stack

The classic test base for this project. All recommendations are grounded in
the local manifest (`pyproject.toml`) and configs present in the repo.

| Layer | Tool | Notes |
|---|---|---|
| Unit + integration | Django `TestCase` (built-in runner) | No pytest dependency; tests run via `uv run python manage.py test`. No separate config required — Django auto-discovers `tests.py` files. |
| Database isolation | Django `TestCase` wraps each test in a transaction and rolls back; `setUpTestData` for shared read-only fixtures | Standard Django pattern; no additional mocking library needed for DB isolation. |
| HTTP client | Django `Client` (built-in) | `client.get/post`, `client.force_login`, `follow=True` for redirect chains. Pass `HTTP_HX_REQUEST='true'` header to simulate HTMX requests. |
| Fixture loading | Django `loaddata` + `TestCase.fixtures` attribute | Seed data in `attractions/fixtures/initial_attractions.json`. |
| e2e | none yet — not planned for this rollout | Web-only app; Django integration tests cover the critical save/auth flow cheaper than e2e. Revisit in a future refresh if browser automation is needed. |
| AI-native | none — not justified for this rollout | Classic integration tests give deterministic signal for all six risks. No vision-model layer warranted. |

**Stack grounding tools (current session):**
- Docs: Context7 — available; not queried (Django TestCase is well-established; no version-specific API uncertainty); checked: 2026-06-06
- Search: Exa.ai — available; not queried (stack fully determined from local manifests); checked: 2026-06-06
- Runtime/browser: none — not available in this session; checked: 2026-06-06
- Provider/platform: Linear (issue tracking only) — no quality-gate relevance for test configuration; checked: 2026-06-06

---

## 5. Quality Gates

The full set of gates that must pass before a change reaches production.
"Required after §3 Phase N" means the gate is enforced once that rollout
phase lands; before that, the gate is planned but not wired.

| Gate | Where | Required? | Catches |
|---|---|---|---|
| Lint (`ruff` or equivalent) | local + CI | required | syntactic drift, unused imports |
| Unit + integration (`manage.py test`) | local + CI | required after §3 Phase 1 | logic regressions in views, models, auth/save flow |
| Django system check (`manage.py check --deploy`) | local + CI | required after §3 Phase 3 | settings misconfiguration, missing required env behaviour |
| Post-edit hook (run tests on file save) | local (agent loop) | recommended after §3 Phase 1 | regressions at edit time before commit |

No e2e gate is planned for the current rollout — Django integration tests cover the critical flows at lower cost. No visual diff or multimodal review gate is warranted for the current risk map.

---

## 6. Cookbook Patterns

How to add new tests in this project. Each sub-section is filled in once
the relevant rollout phase ships; before that, the sub-section reads
"TBD — see §3 Phase N."

### 6.1 Adding a Django integration test (view or endpoint)

TBD — see §3 Phase 1 for the browse-first save / auth-gate pattern.

### 6.2 Adding a test for the save + auth redirect flow

TBD — see §3 Phase 1 for the save-persistence-across-auth-redirect pattern.

### 6.3 Adding an HTMX partial test

TBD — see §3 Phase 2 for the `HTTP_HX_REQUEST` partial-response pattern.

### 6.4 Adding a fixture data quality test

TBD — see §3 Phase 3 for the seed-data field-constraint assertion pattern.

### 6.5 Per-rollout-phase notes

(Appended as phases complete.)

---

## 7. What We Deliberately Don't Test

Exclusions agreed during the rollout (Phase 2 interview, Q5). Future
contributors should respect these unless the underlying assumption changes.

- **Django built-in auth internals (login view, session creation, password hashing)** — the framework ships its own test suite for these; covering them here creates maintenance burden with zero signal gain. Re-evaluate if the project replaces Django's auth with a custom implementation. (Source: interview Q5.)
- **Admin interface** — operator-only surface, tiny blast radius; a misconfigured admin does not affect any user-facing flow. Re-evaluate if admin actions gain side-effects on user data. (Source: implied by flat role model + PRD §Non-Goals "no admin role in MVP".)
- **Generated migration files** — `makemigrations` output is deterministic from model changes; testing generated files tests Django's generator, not the application. Re-evaluate if migrations include `RunPython` data transforms. (Source: PRD §Business Logic — categorization is the app's decision, not a migration transform.)

---

## 8. Freshness Ledger

- Strategy (§1–§5) last reviewed: 2026-06-06
- Stack versions last verified: 2026-06-06
- AI-native tool references last verified: 2026-06-06 (none in use)

Refresh (`/10x-test-plan --refresh`) when:

- a new top-3 risk surfaces from the roadmap or archive,
- a recommended tool's `checked:` date is older than three months,
- the project's tech stack changes (new test runner, Playwright added),
- §7 negative-space no longer matches what the team believes.

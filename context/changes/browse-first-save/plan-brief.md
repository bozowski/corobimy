# Browse-first Save — Plan Brief

> Full plan: `context/changes/browse-first-save/plan.md`
> Research: `context/changes/browse-first-save/research.md`

## What & Why

Allow any user to click "Save" on an attraction card before creating an account. After completing registration or login, the saved attraction appears in their account automatically. This is S-02 — the first user-action feature of the app beyond browsing.

## Starting Point

S-01 (attraction-browse-feed) is complete and approved: `Attraction` model, HTMX filter/pagination, 12 Kraków seed fixtures, 14 passing tests. Session middleware, auth middleware, and `django.contrib.auth` are already wired in settings. Nothing else for saves or auth exists.

## Desired End State

An attraction card has a "Save" button. Anonymous users who click it are redirected to login/register; after completing auth, they are automatically redirected back and the save executes. Authenticated users who click save see "Saved ✓" immediately after redirect. Each user's saved list is isolated from other users'.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Pre-auth save strategy | `?next=` URL + `@login_required` | No session buffer needed — Django's `login()` redirects back to the save URL after auth, and `get_or_create` makes the save idempotent on GET | Research (Exa + Django docs) |
| HTMX save button (anonymous) | Plain HTML form POST | Simplest and testable; auth redirect handles page navigation; HTMX enhancement deferred | Plan |
| Auth views location | New `accounts/` Django app | Clean separation, Django convention, extensible later | Plan |
| Post-save redirect | Back to browse page `/` | Minimal scope — no saved-list page needed in S-02 | Plan |
| Unsave support | Out of scope (save-only) | Keeps S-02 focused; toggle is a future slice | Plan |
| Automated tests | Deferred to `testing-s02-critical-path` | The parallel testing change owns Risks #1–#3 proof; manual verification gates each phase here | Plan |

## Scope

**In scope:**
- `UserSavedAttraction` model (FK User + FK Attraction, unique_together)
- Save view at `attractions/<int:pk>/save/` with `@login_required`
- `accounts/` app: register view + `django.contrib.auth.urls` for login/logout
- Login, logout, register templates (extending `base.html`)
- Save button + "Saved ✓" indicator in `filter_results.html` and `cards_append.html`
- `LOGIN_REDIRECT_URL = '/'` setting

**Out of scope:**
- Unsave / toggle
- `/saved/` attractions list page
- HTMX-optimized save button (no full-page reload)
- Email auth, password reset, social login
- Automated tests (owned by `testing-s02-critical-path`)

## Architecture / Approach

```
Anonymous user → clicks Save (plain form POST) → @login_required intercepts
    → GET /accounts/login/?next=/attractions/<pk>/save/
    → user logs in (or registers via /accounts/register/)
    → Django redirects to GET /attractions/<pk>/save/
    → save_attraction view: get_or_create(user, attraction)
    → redirect('/')
    → browse page shows "Saved ✓" on the card (saved_pks in context)
```

The `attraction_list` view passes `saved_pks` (set of saved attraction PKs for current user) in context to all three render paths — full-page, HTMX filter partial, HTMX load-more partial.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. UserSavedAttraction model | DB table, admin registration | None — standard model addition |
| 2. Save endpoint | Save view, URL, `saved_pks` context, `LOGIN_REDIRECT_URL` | Save view must handle GET (from `?next=` redirect) not just POST |
| 3. accounts/ app | Login, register, logout views + templates | Login template must preserve `{{ next }}` hidden field for `?next=` to survive the form submit |
| 4. Save button in templates | Full user-visible flow wired end-to-end | HTMX partial tests in `attractions/tests.py` may break if template change is malformed |

**Prerequisites:** S-01 complete (✓). PostgreSQL accessible locally (or SQLite for development — `dj_database_url` falls back to SQLite).  
**Estimated effort:** ~2 sessions across 4 phases.

## Open Risks & Assumptions

- `UserCreationForm` asks for username + two passwords — if the PRD requires email-only auth, the register view needs a custom form (not addressed in this plan)
- `LOGIN_REDIRECT_URL = '/'` is the browse page — if a `/saved/` page is added in a future slice, this setting will need updating
- The `testing-s02-critical-path` change must be planned and run after this change ships; until then, Risk #1 (save-persists-across-redirect) has no automated proof

## Success Criteria (Summary)

- Anonymous user completes the full browse-first-save flow (save → login → saved ✓) without losing the save intent
- Anonymous POST to the save URL is server-side rejected (302 to login, zero DB rows)
- Two different users see only their own saved attractions

---
date: 2026-06-12T12:00:00+02:00
researcher: Przemek
git_commit: 7c63a1c5d19aaf35e50d9fe779e6274ee1d06627
branch: main
repository: corobimy
topic: "Browse-first save: current state, implementation shape, and test requirements"
tags: [research, codebase, attractions, auth, save, session, htmx, django]
status: complete
last_updated: 2026-06-12
last_updated_by: Przemek
---

# Research: Browse-first save

**Date**: 2026-06-12  
**Researcher**: Przemek  
**Git Commit**: 7c63a1c5d19aaf35e50d9fe779e6274ee1d06627  
**Branch**: main  
**Repository**: corobimy

---

## Research Question

What is the current state of the browse-first-save feature? What exists in the codebase, what needs to be built, what Django patterns apply, and what test requirements does the test plan impose?

---

## Summary

The browse-first-save feature is entirely greenfield. The `Attraction` model and the HTMX browse feed (S-01) are complete. The Django session and auth middleware are wired and ready. Nothing else for S-02 exists: no `UserSavedAttraction` model, no save endpoint, no auth views, no session pre-auth buffer, no save button in templates.

The canonical Django pattern for this flow is: store `request.session['pending_save'] = attraction_id` on the anonymous save attempt, redirect to login, then consume the key in a `user_logged_in` signal receiver — Django's `login()` uses `cycle_key()` (not `flush()`), so anonymous session data survives the authentication.

The test plan (§2 Risks #1–#3) defines the acceptance floor: save persists across auth redirect, anonymous POST is server-side rejected, and saves are user-scoped. All three are completely untested because the feature code does not yet exist.

---

## Detailed Findings

### What is already built (S-01 complete)

- **`Attraction` model** — `attractions/models.py:11–21`  
  Fields: `name` (CharField 200), `category` (4 choices: family/couples/sport/culture), `description` (TextField), `created_at` (auto). Default ordering: alphabetical by name. No ForeignKey to `User`, no save/bookmark fields.

- **HTMX browse view** — `attractions/views.py:8–28`  
  GET-only. Handles full-page, `filter_results` partial (HTMX category filter), and `cards_append` partial (HTMX load-more). No POST handler, no auth decorator.

- **URL** — `attractions/urls.py:4–6`  
  Single pattern: `path('', views.attraction_list, name='attraction-list')`. No save route.

- **Templates** (4 files total):
  - `templates/base.html` — Tailwind CDN, `{% htmx_script %}`, no auth UI
  - `attractions/templates/attractions/list.html` — category filter form with `hx-get` / `hx-target` / `hx-swap`
  - `attractions/templates/attractions/partials/filter_results.html` — attraction cards + load-more button with `hx-get` / `hx-swap="beforeend"`
  - `attractions/templates/attractions/partials/cards_append.html` — additional cards + OOB load-more update (`hx-swap-oob="true"`)
  
  **None contain a save button, `{% if user.is_authenticated %}` check, `hx-post`, or redirect-next logic.**

- **Seed fixture** — `attractions/fixtures/initial_attractions.json` — 12 Kraków attractions.

- **Infrastructure wired in `corobimy/settings.py`**:
  - `django.contrib.auth` in `INSTALLED_APPS` (line 38)
  - `django.contrib.sessions` in `INSTALLED_APPS` (line 40)
  - `SessionMiddleware` in `MIDDLEWARE` (line 52 — must stay first before auth)
  - `AuthenticationMiddleware` in `MIDDLEWARE` (line 55)
  - `django.contrib.auth.context_processors.auth` in TEMPLATES (line 70)
  - `SESSION_ENGINE` — not set → defaults to `django.contrib.sessions.backends.db` (Postgres-backed, ready)
  - `SESSION_COOKIE_AGE` — not set → defaults to 1209600 s (2 weeks, fine for anonymous buffer)
  - `LOGIN_REDIRECT_URL` — **not set** → defaults to `/accounts/profile/` (must be set for S-02)
  - `AUTHENTICATION_BACKENDS` — not set → standard `ModelBackend` (sufficient)

- **`corobimy/urls.py`** — `/admin/`, `/health/`, attractions root. No `django.contrib.auth.urls` included, no custom login URL.

- **Existing test suite** (`attractions/tests.py:1–111`, `corobimy/tests.py:1–9`):

  | Class | Methods |
  |---|---|
  | `AttractionModelTest` | `test_str_returns_name`, `test_default_ordering_is_alphabetical` |
  | `AttractionListViewTest` | `test_full_page_returns_200`, `test_full_page_has_filter_form`, `test_htmx_category_change_uses_partial`, `test_htmx_category_change_returns_only_matching`, `test_htmx_load_more_uses_cards_append`, `test_htmx_load_more_appends_correct_slice`, `test_no_load_more_when_filtered`, `test_empty_state_when_no_matches` |
  | `AttractionFilterTest` | `test_no_filter_returns_all`, `test_category_filter_returns_correct_queryset`, `test_empty_label_allows_unfiltered` |
  | `HealthCheckTest` (corobimy/tests.py) | `test_health_returns_ok` |

  **All tests use `self.client.get`. Zero POST tests. No save, auth, session, or user-scope tests exist.** Coverage gap maps exactly to test-plan §2 Risks #1–#3.

---

### What needs to be built (S-02 scope)

Five greenfield components, in dependency order:

| # | Component | Notes |
|---|---|---|
| 1 | `UserSavedAttraction` model | `ForeignKey(User, on_delete=CASCADE)`, `ForeignKey(Attraction, on_delete=CASCADE)`, `unique_together = ('user', 'attraction')` — prevents double-saves |
| 2 | Save view + URL | `POST /attractions/<pk>/save/` decorated with `@login_required`; creates `UserSavedAttraction` row; returns HTMX partial (save confirmation) or redirect |
| 3 | Auth views (`accounts/` app) | Registration + login views; `django.contrib.auth.urls` or a thin custom wrapper; sets `LOGIN_URL` and `LOGIN_REDIRECT_URL` in settings |
| 4 | Pre-auth session buffer | On anonymous save attempt: write `request.session['pending_save'] = attraction_id`, redirect to `login?next=/attractions/<pk>/save/` — **or** intercept upstream in a custom view before the `@login_required` bounce |
| 5 | Post-login handler | Consume `session.pop('pending_save', None)` after login — see Django pattern below |

---

### Django pattern: session buffer + `user_logged_in` signal

**Why the session survives login:** Django's `login()` calls `request.session.cycle_key()` — it rotates the session key for security but does **not** flush the data. Any key written to the anonymous session (including `pending_save`) is still present after the user authenticates. This is guaranteed by Django's own auth docs and `django/contrib/auth/__init__.py`.

**Pre-auth intercept (option A — custom save view wrapper):**
```python
# attractions/views.py
def save_attraction(request, pk):
    if not request.user.is_authenticated:
        request.session['pending_save'] = pk
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")
    attraction = get_object_or_404(Attraction, pk=pk)
    UserSavedAttraction.objects.get_or_create(user=request.user, attraction=attraction)
    return HttpResponse(...)  # HTMX partial
```
Advantage: no signal needed; `pending_save` is set before the redirect, consumed in the same view after login redirects back via `?next=`.

**Post-login signal (option B — decoupled):**
```python
# accounts/signals.py
from django.contrib.auth.signals import user_logged_in

@receiver(user_logged_in)
def execute_pending_save(sender, request, user, **kwargs):
    attraction_id = request.session.pop('pending_save', None)
    if attraction_id:
        UserSavedAttraction.objects.get_or_create(user=user, attraction_id=attraction_id)
```
Fires for both login AND registration (since registration calls `login()` internally). Register in `AppConfig.ready()`.

**Recommended approach:** Option A (custom wrapper) for the anonymous intercept + rely on `?next=` to return to the save URL. This means `@login_required` alone is sufficient; the redirect back to the save URL after login automatically completes the save. No signal needed. Simpler, more testable (one code path to trace).

**Decided open question from roadmap S-02:** "How should post-auth redirect preserve the pending save — session-based pre-auth buffer, URL parameter, or client-side state?" → The `?next=` URL approach + `@login_required` is the simplest: the pending save is encoded in the URL, not the session, and executed when `@login_required` returns control to the save view after auth. The session key approach is a fallback if the save view cannot be re-entered via `?next=`.

---

### Test requirements (from test-plan.md §2)

The test plan defines three risks that S-02 must protect against. The parallel testing change (`testing-s02-critical-path`) will own these tests, but the S-02 implementation must be built to make them pass.

**Risk #1 — Save persists across auth redirect** (High impact / High likelihood)  
_Scenario:_ Anonymous user clicks save → redirected to register/login → completes auth → attraction present in account.  
_Test shape:_ Django integration test with `follow=True` — must assert the save exists in the DB, not just that login succeeded.  
_What the implementation must enable:_ A redirect chain from anonymous save attempt through login/register back to a save-executing endpoint; the chain must terminate with a `UserSavedAttraction` row in the DB.

**Risk #2 — Save endpoint server-side auth enforcement** (High impact / Medium likelihood)  
_Scenario:_ Anonymous `POST /attractions/<pk>/save/` must return 302→login (or 403) and create zero DB rows.  
_Test shape:_ `self.client.post(save_url)` without login; assert redirect and `UserSavedAttraction.objects.count() == 0`.  
_What the implementation must enable:_ `@login_required` (or equivalent) on the save view.

**Risk #3 — User-scope isolation** (High impact / Low likelihood)  
_Scenario:_ User A's saves are absent from User B's saved list response.  
_Test shape:_ Two-user test; assert User B's view does not include User A's save.  
_What the implementation must enable:_ Saves queryset filtered by `user=request.user`.

---

## Code References

- `attractions/models.py:11–21` — `Attraction` model (FK target for `UserSavedAttraction`)
- `attractions/views.py:8–28` — browse view (reference for adding save endpoint alongside)
- `attractions/urls.py:4–6` — URL patterns (add save route here)
- `attractions/templates/attractions/partials/filter_results.html:3–6` — attraction cards (add save button here)
- `attractions/templates/attractions/partials/cards_append.html:1–6` — load-more cards (add save button here too)
- `corobimy/settings.py:36–57` — INSTALLED_APPS + MIDDLEWARE baseline
- `corobimy/urls.py:21–25` — URL root (add `path('accounts/', include('django.contrib.auth.urls'))` or `accounts/` app)
- `attractions/tests.py:1–111` — existing test suite (all GET; save tests go in a new class here or in testing-s02-critical-path)

---

## Architecture Insights

1. **HTMX POST for save button**: The browse feed already uses HTMX GET for filtering/pagination. The save button should use `hx-post` + `hx-target` to swap the button state (saved/unsaved) without a full-page reload. For anonymous users, the HTMX POST still hits the server; the server redirects, but HTMX follows same-origin 3xx responses — this means anonymous save via HTMX must be handled carefully (consider returning `HX-Redirect` header instead of a 302, so HTMX drives the navigation).

2. **Session key naming**: Use a short, collision-resistant key. `pending_save` is fine; it holds a single integer (attraction PK). No need for a list — the user can only be saving one attraction at a time via UI.

3. **`unique_together` on `UserSavedAttraction`**: Prevents double-saves from HTMX rapid-clicks or repeated requests. Use `get_or_create` in the view for idempotency.

4. **`LOGIN_REDIRECT_URL` must be set**: Currently defaults to `/accounts/profile/` which doesn't exist. Set to `'/'` or a meaningful saved-list URL.

5. **No `accounts/` app exists**: Auth views (login, register, logout) need a home. The simplest path is `django.contrib.auth.urls` included at `accounts/` — gives login, logout, password-change for free. Register needs a custom view.

---

## Historical Context

- `context/changes/testing-s02-critical-path/change.md` — status `new` (change opened 2026-06-06), no research or plan yet. This is the parallel testing track for Risks #1–#3 from test-plan §3 Phase 1.
- `context/changes/browse-first-save/change.md` — this change, status `preparing`, created 2026-06-12.
- Roadmap S-01 complete (2026-06-04, impl-review APPROVED). S-02 status: `proposed`.
- The roadmap's open S-02 unknown on pre-auth buffer strategy is resolved by this research: `?next=` + `@login_required` is the simplest approach; session key is the fallback.

---

## Open Questions

1. **Where should the saved-attractions list live?** A new `/saved/` page, or a profile page? This determines the `LOGIN_REDIRECT_URL` value and where the user lands after auth.
2. **HTMX save button for anonymous users**: Should the server return `HX-Redirect` to navigate the full page to login, or should the save button do a full-page form POST (non-HTMX) for anonymous users and HTMX POST only for authenticated? The full-page approach is simpler and more accessible.
3. **Registration form**: Django's built-in `UserCreationForm` or a custom one with email only? The PRD should clarify.
4. **Save button UI state**: After saving, the button should change to "saved" state. Does unsaving need to be supported in S-02?
5. **`testing-s02-critical-path` timing**: Should tests be written before or after implementing the feature? Test-plan §3 shows it as a parallel change — the plan should decide whether tests lead or follow implementation.

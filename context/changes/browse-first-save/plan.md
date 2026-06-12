# Browse-first Save Implementation Plan

## Overview

Implement the browse-first-save feature (S-02): an anonymous user can click "Save" on any attraction card, complete registration or login, and find that attraction saved in their account — without losing the save intent across the auth redirect. This is entirely greenfield; the browse feed (S-01) is the only existing feature.

## Current State Analysis

The attraction browse feed is complete and stable (S-01, approved). Everything related to saves, auth, and accounts is missing:

- `Attraction` model exists at `attractions/models.py:11–21` — 4 fields, no User FK, no save relationship
- `attraction_list` view exists at `attractions/views.py:8–28` — GET-only, no POST handler, no auth decorator
- Session middleware, auth middleware, and `django.contrib.auth` are all wired in `corobimy/settings.py:36–57` — ready to use with no changes needed beyond `LOGIN_REDIRECT_URL`
- `LOGIN_REDIRECT_URL` is unset — defaults to `/accounts/profile/` which doesn't exist; must be set to `'/'`
- No `accounts/` app, no auth URLs registered, no login/register templates
- `templates/base.html:10` sets `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` on body — HTMX requests auto-include CSRF; plain form POSTs still need `{% csrf_token %}` in the form

### Key Discoveries

- `list.html:22` uses `{% include "attractions/partials/filter_results.html" %}` — context flows through the include, so `saved_pks` added to the view context is available in the partial on initial full-page loads and on HTMX filter swaps
- `cards_append.html` renders bare card divs (no grid wrapper); `filter_results.html` renders cards inside `#attraction-grid`; save button must be added to both
- `django.contrib.auth.urls` default login URL is `/accounts/login/` — this matches the Django default for `LOGIN_URL` and requires no explicit settings entry if auth URLs are mounted at `accounts/`
- The `?next=` mechanism (used by `@login_required`) redirects to the save URL as a GET after login — the save view must therefore create the save on any authenticated request (GET or POST), relying on `get_or_create` idempotency

## Desired End State

A logged-in user can save an attraction by clicking the save button on any card. An anonymous user who clicks save is redirected to login or register; after completing auth, they are redirected back to the save URL and the save is created automatically. Each user's save list is isolated — no cross-user leakage. The save button shows "Saved ✓" for already-saved attractions.

### Verification

- Full browse-first-save redirect chain: anonymous → save click → login → attraction in DB, "Saved ✓" shown
- Anonymous POST to save URL → 302 to `/accounts/login/?next=<save-url>`, zero DB rows created
- User A's saves not visible in User B's session/context

## What We're NOT Doing

- Unsave / toggle (save-only in S-02; toggle is a future slice)
- `/saved/` saved-attractions list page (post-save redirects to `/`)
- HTMX enhancement on the save button for authenticated users (plain form POST for all users)
- Email-based registration (Django's built-in `UserCreationForm` with username)
- Password reset, email verification, social auth
- Automated tests for the save flow (owned by the parallel change `testing-s02-critical-path`)
- The `testing-s02-critical-path` change itself — this plan ships the implementation only

## Implementation Approach

Four independent phases in dependency order: model foundation → save endpoint → auth views → UI wiring. Each phase is verifiable before the next begins. The full redirect chain is testable only after Phase 4.

The anonymous save redirect uses `@login_required` + Django's built-in `?next=` mechanism. After login, Django redirects the browser to `GET <save-url>`. The save view handles any authenticated request (GET or POST) with `get_or_create`, so the GET from `?next=` executes the save idempotently. No session buffer or signal is needed.

## Critical Implementation Details

**GET-or-POST save view**: Django's `@login_required` redirects to the save URL as a GET after login, not a POST. The save view must not restrict to `POST` only — it must create the save on any authenticated request. `get_or_create` makes this safe and idempotent.

**`saved_pks` context for HTMX partials**: The `attraction_list` view must compute `saved_pks` before the `request.htmx` branch so it flows into all three render paths (list.html full-page, filter_results.html HTMX swap, cards_append.html load-more).

---

## Phase 1: UserSavedAttraction Model

### Overview

Define the join model that records which attractions a user has saved. This is the data layer that all subsequent phases depend on.

### Changes Required

#### 1. Add `UserSavedAttraction` to models

**File**: `attractions/models.py`

**Intent**: Add a join model between `User` and `Attraction` that records a user's saved attractions, prevents duplicates, and preserves save order.

**Contract**:
- `user` — `ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='saved_attractions')`
- `attraction` — `ForeignKey(Attraction, on_delete=CASCADE, related_name='saves')`
- `saved_at` — `DateTimeField(auto_now_add=True)`
- `Meta.unique_together = [('user', 'attraction')]`
- `Meta.ordering = ['-saved_at']`
- `__str__` returns `f"{self.user} → {self.attraction}"`
- Import `settings` from `django.conf`

#### 2. Generate and apply migration

**File**: `attractions/migrations/` (auto-generated)

**Intent**: Produce and apply the schema migration for `UserSavedAttraction`.

**Contract**: `uv run python manage.py makemigrations attractions` then `uv run python manage.py migrate`.

#### 3. Register in admin

**File**: `attractions/admin.py`

**Intent**: Make `UserSavedAttraction` visible and editable in Django admin for manual inspection during development.

**Contract**: `admin.site.register(UserSavedAttraction)` alongside the existing `AttractionAdmin`. Import `UserSavedAttraction` at the top.

### Success Criteria

#### Automated Verification

- `uv run python manage.py migrate` applies without error
- `uv run python manage.py check` reports no issues
- `uv run python manage.py test` — all 14 existing tests still pass

#### Manual Verification

- `UserSavedAttraction` appears in Django admin at `/admin/attractions/usersavedattraction/`
- Admin form allows creating a save record linking a user to an attraction
- Attempting to create a duplicate (same user + attraction) fails with a unique constraint error in the admin

**Implementation Note**: After completing Phase 1 and all automated verification passes, pause for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Save Endpoint

### Overview

Add the save view and URL that creates a `UserSavedAttraction` row, update the browse view to pass `saved_pks` in context, and set `LOGIN_REDIRECT_URL`.

### Changes Required

#### 1. Add `save_attraction` view

**File**: `attractions/views.py`

**Intent**: Handle save requests for any authenticated user. Anonymous requests are intercepted by `@login_required` and redirected to login with `?next=<save-url>`; after login, Django GETs this same URL and the save is created.

**Contract**:
- Decorated with `@login_required` (import from `django.contrib.auth.decorators`)
- Accepts `request` and `pk` (int) — no method restriction; handles both POST and the GET from `?next=` redirect
- `get_object_or_404(Attraction, pk=pk)` to 404 on invalid pk
- `UserSavedAttraction.objects.get_or_create(user=request.user, attraction=attraction)` — idempotent
- Returns `redirect('/')` (import `redirect` from `django.shortcuts`)

#### 2. Add `saved_pks` to `attraction_list` context

**File**: `attractions/views.py`

**Intent**: Let templates know which attractions the current user has already saved, so they can render the correct button state.

**Contract**: Add to the `context` dict before the `request.htmx` branch:
- If `request.user.is_authenticated`: `saved_pks = set(UserSavedAttraction.objects.filter(user=request.user).values_list('attraction_id', flat=True))`
- Else: `saved_pks = set()`
- Pass as `'saved_pks': saved_pks` in `context`

#### 3. Add save URL pattern

**File**: `attractions/urls.py`

**Intent**: Route POST and GET requests to the save view.

**Contract**: `path('attractions/<int:pk>/save/', views.save_attraction, name='attraction-save')` added to `urlpatterns`.

#### 4. Set `LOGIN_REDIRECT_URL`

**File**: `corobimy/settings.py`

**Intent**: Ensure users who log in without a `?next=` parameter land on the browse page, not the Django default `/accounts/profile/`.

**Contract**: Add `LOGIN_REDIRECT_URL = '/'` near the other auth-related settings (after `AUTH_PASSWORD_VALIDATORS` or at the bottom of settings).

### Success Criteria

#### Automated Verification

- `uv run python manage.py check` — no issues
- `uv run python manage.py test` — all existing tests still pass

#### Manual Verification

- Authenticated POST to `/attractions/1/save/` → creates a `UserSavedAttraction` row in DB, redirects to `/`
- Anonymous POST to `/attractions/1/save/` → 302 to `/accounts/login/?next=/attractions/1/save/` (login URL not yet functional until Phase 3, but the redirect must exist)
- `attraction_list` view response context includes `saved_pks` (verify in Django shell or by adding a temporary `{{ saved_pks }}` to the template)

**Implementation Note**: After completing Phase 2 and all automated verification passes, pause for manual confirmation before proceeding to Phase 3.

---

## Phase 3: accounts/ App — Auth Views and Templates

### Overview

Create the `accounts/` Django app with a register view, wire Django's built-in auth URLs for login/logout, and create the required templates. After this phase, the full `?next=` redirect chain becomes functional.

### Changes Required

#### 1. Create `accounts/` app

**File**: `accounts/` directory (new)

**Intent**: House auth views (register) in a dedicated app, following Django's convention for separating auth concerns from feature apps.

**Contract**: Create the directory and files:
- `accounts/__init__.py` — empty
- `accounts/apps.py` — `AccountsConfig` with `name = 'accounts'`
- `accounts/views.py` — register view (see below)
- `accounts/urls.py` — URL patterns (see below)
- `accounts/templates/accounts/` — template directory for register

#### 2. Register view

**File**: `accounts/views.py`

**Intent**: Allow new users to create an account using Django's built-in `UserCreationForm`, then log them in immediately and redirect to `LOGIN_REDIRECT_URL`.

**Contract**:
- `register(request)` function view
- `from django.contrib.auth.forms import UserCreationForm`
- `from django.contrib import auth as django_auth`
- On valid POST: `form.save()` → `django_auth.login(request, user)` → `redirect(settings.LOGIN_REDIRECT_URL)` where `user = form.save()`
- On GET or invalid POST: render `'accounts/register.html'` with `{'form': form}`

#### 3. accounts URL patterns

**File**: `accounts/urls.py`

**Intent**: Expose the register view at `/accounts/register/`.

**Contract**: `path('register/', views.register, name='register')` in `urlpatterns`.

#### 4. Wire URLs in root URLconf

**File**: `corobimy/urls.py`

**Intent**: Mount Django's built-in auth views (login, logout) and the custom register view under `accounts/`.

**Contract**: Add two includes to `urlpatterns`:
- `path('accounts/', include('django.contrib.auth.urls'))` — provides login, logout, password-change, etc.
- `path('accounts/', include('accounts.urls'))` — provides register

Both at `accounts/`; Django resolves by first match among the two includes.

#### 5. Add accounts to INSTALLED_APPS

**File**: `corobimy/settings.py`

**Intent**: Register the `accounts` app so Django discovers its templates and can run its AppConfig.

**Contract**: Add `'accounts'` to `INSTALLED_APPS` list.

#### 6. Login template

**File**: `templates/registration/login.html`

**Intent**: Render Django's built-in login view. The `registration/` path is required by `django.contrib.auth.urls`.

**Contract**:
- Extends `base.html`
- Contains a `<form method="post">` with `{% csrf_token %}`, `{{ form.as_p }}`, hidden `<input type="hidden" name="next" value="{{ next }}">` to preserve the `?next=` parameter, and a submit button
- Tailwind styling consistent with existing pages

#### 7. Logout template

**File**: `templates/registration/logged_out.html`

**Intent**: Render confirmation after logout, with a link back to the browse page.

**Contract**: Extends `base.html`. Shows a "You have been logged out." message and a link to `{% url 'attraction-list' %}`.

#### 8. Register template

**File**: `accounts/templates/accounts/register.html`

**Intent**: Render the registration form with `UserCreationForm` fields.

**Contract**:
- Extends `base.html`
- `<form method="post">` with `{% csrf_token %}`, `{{ form.as_p }}`, submit button
- Tailwind styling consistent with existing pages
- Optionally: link to login page for existing users

### Success Criteria

#### Automated Verification

- `uv run python manage.py check` — no issues
- `uv run python manage.py test` — all existing tests still pass

#### Manual Verification

- `GET /accounts/login/` — renders login form with username/password fields
- `POST /accounts/login/` with valid credentials → redirect to `/` (browse page)
- `POST /accounts/login/` with `?next=/attractions/1/save/` → after login, redirect to `/attractions/1/save/` → save created → redirect to `/`
- `GET /accounts/register/` — renders register form with username/password1/password2 fields
- `POST /accounts/register/` with valid data → creates user, logs in, redirects to `/`
- `POST /accounts/logout/` → logs out, renders logged_out page with link to browse
- No regression in existing browse, filter, and load-more functionality

**Implementation Note**: After completing Phase 3 and all automated verification passes, pause for manual confirmation (including the full login+redirect chain) before proceeding to Phase 4.

---

## Phase 4: Save Button in Templates

### Overview

Add the save button to each attraction card in `filter_results.html` and `cards_append.html`. Authenticated users who have already saved an attraction see "Saved ✓"; others see a save form. This phase wires the full browse-first-save user flow.

### Changes Required

#### 1. Save button in `filter_results.html`

**File**: `attractions/templates/attractions/partials/filter_results.html`

**Intent**: Render a save button (or saved indicator) on each card in the main card grid.

**Contract**: Inside the `{% for attraction in attractions %}` loop, after the description `<p>`, add:
- `{% if attraction.pk in saved_pks %}` — render a non-interactive "Saved ✓" span
- `{% else %}` — render `<form method="post" action="{% url 'attraction-save' attraction.pk %}">{% csrf_token %}<button type="submit">Save</button></form>`
- `{% endif %}`
- Tailwind styling consistent with the card's existing design

#### 2. Save button in `cards_append.html`

**File**: `attractions/templates/attractions/partials/cards_append.html`

**Intent**: Mirror the save button in the load-more partial so additional cards loaded via HTMX also have the correct button state.

**Contract**: Same `{% if attraction.pk in saved_pks %}` / form pattern as in `filter_results.html`, applied inside the `{% for attraction in attractions %}` loop. The `saved_pks` set is passed through from the `attraction_list` view context.

### Success Criteria

#### Automated Verification

- `uv run python manage.py test` — all 14 existing tests still pass (including HTMX partial template tests)
- `uv run python manage.py check` — no issues

#### Manual Verification

- Browse page shows a save button on each attraction card
- Authenticated user: clicks save button → save created → redirect to `/` → card shows "Saved ✓" on return
- Anonymous user: clicks save button → redirected to `/accounts/login/?next=/attractions/<pk>/save/` → logs in → attraction saved → redirect to `/` → card shows "Saved ✓"
- Anonymous user via register: same flow but using `/accounts/register/` instead of login
- Load-more attractions (via HTMX "Load more" button) show save buttons with correct state for each card
- Filter (HTMX category change) re-renders with correct saved state on visible cards
- "Saved ✓" indicator appears on all previously saved attractions on page load
- No regression: filter, load-more, empty state, category display all work as before

**Implementation Note**: After completing Phase 4 and all automated verification passes, pause for full manual confirmation of the end-to-end browse-first-save flow before declaring this change complete.

---

## Testing Strategy

### Tests in This Change

None — by design. Automated tests for the save flow (Risk #1 redirect chain, Risk #2 auth gate, Risk #3 user-scope isolation) are owned by the parallel change `testing-s02-critical-path`. The success criteria above define the manual verification floor.

### Existing Tests That Must Keep Passing

All 13 tests in `attractions/tests.py` and the 1 health check test in `corobimy/tests.py` must pass throughout all phases. The `AttractionListViewTest` HTMX partial tests are the highest-regression risk when modifying templates — run `uv run python manage.py test` after Phase 4 template changes.

### Manual Testing Steps

1. Start dev server: `uv run python manage.py runserver`
2. Browse to `http://localhost:8000/`
3. Verify save buttons appear on cards
4. As anonymous user: click save → verify redirect to login
5. Complete login → verify redirected to save URL → verify "Saved ✓" shown
6. Log out → register as a new user → click save → verify same flow works via register
7. Filter by category → verify save buttons still appear on filtered cards
8. Load more → verify save buttons appear on newly loaded cards
9. Reload page as authenticated user → verify "Saved ✓" persists on previously saved cards
10. Open private window → log in as a different user → verify their save list is empty (user-scope isolation)

## Migration Notes

Standard Django migration. No data migration needed — `UserSavedAttraction` is a new table with no existing data to transform.

To verify: `uv run python manage.py showmigrations attractions` should show `0002_usersavedattraction` (or equivalent name) applied after Phase 1.

## References

- Research doc: `context/changes/browse-first-save/research.md`
- Parallel testing change: `context/changes/testing-s02-critical-path/change.md`
- Test plan (risks + quality gates): `context/foundation/test-plan.md`
- `attractions/models.py:11–21` — `Attraction` model (FK target)
- `attractions/views.py:8–28` — browse view (reference for save endpoint pattern)
- `attractions/templates/attractions/partials/filter_results.html` — primary card template
- `attractions/templates/attractions/partials/cards_append.html` — load-more card template
- `templates/base.html:10` — `hx-headers` CSRF pattern

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: UserSavedAttraction Model

#### Automated

- [x] 1.1 Migration applies without error (`uv run python manage.py migrate`) — c95b465
- [x] 1.2 System check passes (`uv run python manage.py check`) — c95b465
- [x] 1.3 All existing tests pass (`uv run python manage.py test`) — c95b465

#### Manual

- [x] 1.4 `UserSavedAttraction` visible in Django admin at `/admin/attractions/usersavedattraction/` — c95b465
- [x] 1.5 Admin form creates a save record; duplicate (same user + attraction) fails with unique constraint — c95b465

### Phase 2: Save Endpoint

#### Automated

- [x] 2.1 System check passes (`uv run python manage.py check`) — bcad1c0
- [x] 2.2 All existing tests pass (`uv run python manage.py test`) — bcad1c0

#### Manual

- [x] 2.3 Authenticated POST to `/attractions/1/save/` creates DB row, redirects to `/` — bcad1c0
- [x] 2.4 Anonymous POST to `/attractions/1/save/` returns 302 to `/accounts/login/?next=/attractions/1/save/` — bcad1c0
- [x] 2.5 `attraction_list` context includes `saved_pks` (non-empty set for a user with saves) — bcad1c0

### Phase 3: accounts/ App

#### Automated

- [x] 3.1 System check passes (`uv run python manage.py check`)
- [x] 3.2 All existing tests pass (`uv run python manage.py test`)

#### Manual

- [x] 3.3 `GET /accounts/login/` renders login form
- [x] 3.4 `POST /accounts/login/` with valid credentials redirects to `/`
- [x] 3.5 Login with `?next=/attractions/1/save/` → save created → redirect to `/`
- [x] 3.6 `GET /accounts/register/` renders register form
- [x] 3.7 `POST /accounts/register/` creates user, logs in, redirects to `/`
- [x] 3.8 Logout renders confirmation and link back to browse

### Phase 4: Save Button in Templates

#### Automated

- [ ] 4.1 All existing tests pass (`uv run python manage.py test`)
- [ ] 4.2 System check passes (`uv run python manage.py check`)

#### Manual

- [ ] 4.3 Save buttons appear on all attraction cards on browse page
- [ ] 4.4 Full anonymous-save → login → save-created → "Saved ✓" flow works end-to-end
- [ ] 4.5 Full anonymous-save → register → save-created → "Saved ✓" flow works end-to-end
- [ ] 4.6 Load-more cards show correct save button state
- [ ] 4.7 HTMX filter renders correct save button state on filtered cards
- [ ] 4.8 Two-user isolation: User A's saves not shown as saved to User B
- [ ] 4.9 No regression in filter, load-more, empty state, or category display

# S-02 Critical Path Tests Implementation Plan

## Overview

Write Django integration tests covering Phase 1 risks (#1 save-across-auth-redirect, #2 server-side auth gate, #3 user-scope isolation), fix the confirmed register-path bug that would otherwise make Risk #1's register test permanently fail, and verify all tests pass green.

## Current State Analysis

All three risks are untested — `attractions/tests.py` covers only the browse/filter/HTMX list view. The save endpoint and user-scope logic are correct code with no test coverage; writing tests for them is straightforward.

Risk #1 has a confirmed bug on the register path: `accounts/views.py:13` always redirects to `LOGIN_REDIRECT_URL = '/'` and never reads `?next=`. `templates/registration/login.html:22` compounds this by not forwarding `?next=` in the Register link at all. The login path works correctly end-to-end via Django's built-in auth view.

**Key discoveries:**

- `attractions/views.py:42-48` — `save_attraction` is `@login_required` + `get_or_create`; accepts GET and POST by design (Django redirects back with GET after login)
- `attractions/views.py:18-25` — `saved_pks` is correctly `.filter(user=request.user, ...)`; anonymous users get `set()`
- `attractions/models.py:31` — `unique_together = [('user', 'attraction')]` enforces idempotency at the DB level
- `templates/registration/login.html:22` — register link is `{% url 'register' %}` with no `?next=` forwarded
- `accounts/templates/accounts/register.html:9-18` — register form has `{% csrf_token %}` but no hidden `next` field
- `accounts/views.py:13` — `redirect(settings.LOGIN_REDIRECT_URL)` ignores any `next` param
- Test runner: `uv run python manage.py test`; Django TestCase; existing helper `make_attraction()` in `attractions/tests.py`

## Desired End State

`uv run python manage.py test attractions` runs 16 tests (11 existing + 5 new) and reports zero failures. The five new tests prove:
- An anonymous POST to the save endpoint is rejected server-side with a 302 and creates no DB rows
- A GET with an invalid pk returns 404 for authenticated users
- User B's saved-pk set does not contain User A's saves
- An anonymous user who **logs in** ends up with the save in their account
- An anonymous user who **registers** ends up with the save in their account

A manual walkthrough — anonymous save → Register → complete form → visit attraction list — shows the attraction marked saved.

### Key Discoveries:

- `make_attraction()` helper at `attractions/tests.py:7` is reusable; new classes should call it, not recreate it
- `UserCreationForm` requires `password1` + `password2`; use `User.objects.create_user(username, password=...)` for pre-existing users in test setup, and post to `/accounts/register/` with `password1`/`password2` for the register-path test
- `url_has_allowed_host_and_scheme` is the correct safe-redirect validator; it is available in Django 6.0.5 at `django.utils.http`
- `assertRedirects(..., fetch_redirect_response=False)` avoids following the chain when only the redirect target matters

## What We're NOT Doing

- No HTMX-specific tests (Phase 2 of the test rollout)
- No env/settings/health tests (Phase 3)
- No e2e browser automation
- No idempotency test (duplicate save → single row) — out of scope per user decision; `unique_together` is the technical guarantee
- No admin interface tests
- No migration tests

## Implementation Approach

Three-phase TDD sequence: **green → red → green**.

- Phase 1 writes tests that pass today (Risks #2, #3, and Risk #1 login path) — no code changes needed.
- Phase 2 adds the one failing test (Risk #1 register path) — intentionally red, documenting the bug.
- Phase 3 fixes the register-path bug across three files and turns Phase 2's test green.

Each phase has a clear pass/fail signal before the next begins.

## Critical Implementation Details

**`next` flows through POST, not GET, in the register test.** The test posts directly to `/accounts/register/` with `next=save_url` in the form body. After Phase 3, the register view reads `request.POST.get('next')` — so the test correctly exercises the fixed code path without needing to simulate the template link.

**Open-redirect validation is non-negotiable.** The register view must call `url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})` before redirecting to `next_url`. Skipping this turns `?next=` into an open redirect.

---

## Phase 1: Green tests (Risk #2 auth gate, Risk #3 user isolation, Risk #1 login path)

### Overview

Add three new `TestCase` classes to `attractions/tests.py`. Every test in this phase should pass immediately after the additions, with no changes to any non-test file.

### Changes Required:

#### 1. Add import block for new test dependencies

**File**: `attractions/tests.py`

**Intent**: The new classes need `get_user_model`, `UserSavedAttraction`, and `reverse` (already imported). Add at the top alongside existing imports.

**Contract**: Two new import lines — `from django.contrib.auth import get_user_model` and `from attractions.models import Attraction, UserSavedAttraction` (replace the current single-model import). Add a module-level `User = get_user_model()`.

#### 2. Add `SaveAuthGateTest` class

**File**: `attractions/tests.py`

**Intent**: Prove that the save endpoint enforces authentication server-side, independently of the UI.

**Contract**: `TestCase` subclass with `setUpTestData` creating one `Attraction` and one `User`. Three test methods:

- `test_anonymous_post_is_rejected` — anonymous `client.post` to `attraction-save` url → assert 302 redirects toward `/accounts/login/` AND `UserSavedAttraction.objects.count() == 0`
- `test_authenticated_post_saves_and_redirects` — `force_login` + `client.post` → assert `UserSavedAttraction` row exists for the logged-in user AND response redirects to `attraction-list`
- `test_invalid_pk_returns_404` — `force_login` + `client.get` to `attraction-save` with a pk that does not exist in the DB → assert 404

#### 3. Add `UserSaveIsolationTest` class

**File**: `attractions/tests.py`

**Intent**: Prove that a logged-in user never sees another user's saved attractions in the view context.

**Contract**: `TestCase` subclass with `setUpTestData` creating one `Attraction`, `user_a`, `user_b`, and a `UserSavedAttraction` row for `user_a`. One test method:

- `test_user_b_context_excludes_user_a_saves` — `force_login(user_b)` + GET `attraction-list` → assert `self.attraction.pk not in response.context['saved_pks']`

#### 4. Add `SaveAcrossAuthTest` class (login-path method only)

**File**: `attractions/tests.py`

**Intent**: Prove that the login path of the save-across-auth-redirect flow creates the DB row end-to-end.

**Contract**: `TestCase` subclass with `setUpTestData` creating one `Attraction` and one `User`. One test method in this phase:

- `test_login_path_save_persists` — anonymous `client.post` to save URL → then `client.post('/accounts/login/', {'username': ..., 'password': ..., 'next': save_url}, follow=True)` → assert `UserSavedAttraction.objects.filter(user=cls.user, attraction=cls.attraction).exists()` is `True`

### Success Criteria:

#### Automated Verification:

- `uv run python manage.py test attractions.tests.SaveAuthGateTest` — 3 tests, 0 failures
- `uv run python manage.py test attractions.tests.UserSaveIsolationTest` — 1 test, 0 failures
- `uv run python manage.py test attractions.tests.SaveAcrossAuthTest.test_login_path_save_persists` — 1 test, 0 failures
- `uv run python manage.py test attractions` — full suite (14 tests) passes, 0 failures, 0 errors

#### Manual Verification:

- Skim the test output: the 5 new tests are listed by name and show as `.` (dot = pass), not `F` or `E`

**Implementation Note**: After all automated verification passes, pause here for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Red test (Risk #1 register path)

### Overview

Add the single failing test that proves the register-path bug. This phase ends with exactly one test showing `FAIL` in the output — everything else stays green.

### Changes Required:

#### 1. Add `test_register_path_save_persists` to `SaveAcrossAuthTest`

**File**: `attractions/tests.py`

**Intent**: Prove that an anonymous user who registers (instead of logging in) ends up with the save in their account. This test must fail today — failure is the expected result of this phase.

**Contract**: New method on the existing `SaveAcrossAuthTest` class. Posts to `/accounts/register/` with credentials (`username`, `password1`, `password2`) and `next=save_url` in the form body, with `follow=True`. After the POST chain settles, asserts `UserSavedAttraction.objects.filter(user=<registered_user>, attraction=cls.attraction).exists()` is `True`. The `<registered_user>` is retrieved via `User.objects.get(username=<the_new_username>)` after the post.

### Success Criteria:

#### Automated Verification:

- `uv run python manage.py test attractions.tests.SaveAcrossAuthTest.test_register_path_save_persists` exits with a **FAIL** (AssertionError on the `assertTrue` for the DB row — not an error or exception)
- `uv run python manage.py test attractions` — 15 tests: 14 pass, **1 fails** — all other tests still green

#### Manual Verification:

- The failure message names the missing `UserSavedAttraction` row, not an unexpected import or setup error — confirming the bug is correctly documented

**Implementation Note**: Pause here for manual confirmation of the expected failure before proceeding to Phase 3.

---

## Phase 3: Fix register-path bug

### Overview

Three coordinated file changes forward `?next=` from the login page through to the register view and honour it safely on successful registration. Phase 2's failing test turns green.

### Changes Required:

#### 1. Forward `?next=` in the login template's register link

**File**: `templates/registration/login.html`

**Intent**: The current Register link (`{% url 'register' %}`) drops the `?next=` value the user arrived with. Update it to append `?next=` when a `next` value is present, so the register page receives the pending save URL.

**Contract**: Replace the `<a href="{% url 'register' %}">` with a conditional that appends `?next={{ next|urlencode }}` when `next` is non-empty. The hidden `<input type="hidden" name="next" value="{{ next }}">` at line 11 already exists in the login form — the register link is the only gap.

#### 2. Add hidden `next` field to register form

**File**: `accounts/templates/accounts/register.html`

**Intent**: The register form currently submits only the `UserCreationForm` fields. Add a hidden `next` field so the value from the URL is POSTed along with the credentials on form submit.

**Contract**: Inside the existing `<form method="post">` block, after `{% csrf_token %}`, add `<input type="hidden" name="next" value="{{ next }}">`. The `next` template variable will be populated by the view fix below.

#### 3. Fix register view to read `?next=` and redirect safely

**File**: `accounts/views.py`

**Intent**: After a successful registration, redirect to `next` if it is a safe same-host URL, otherwise fall back to `LOGIN_REDIRECT_URL`. Also pass `next` into the template context on GET so the hidden field can be populated.

**Contract**: Add `from django.utils.http import url_has_allowed_host_and_scheme` to the import block. On POST success, read `next_url = request.POST.get('next', '')`, validate it, and redirect appropriately:

```python
next_url = request.POST.get('next', '')
if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
    return redirect(next_url)
return redirect(settings.LOGIN_REDIRECT_URL)
```

On GET (and on failed POST), pass `'next': request.GET.get('next', '')` in the `render` context dict so the template can emit the hidden field.

### Success Criteria:

#### Automated Verification:

- `uv run python manage.py test attractions.tests.SaveAcrossAuthTest.test_register_path_save_persists` — 1 test, **0 failures** (was red in Phase 2)
- `uv run python manage.py test attractions` — **15 tests, 0 failures, 0 errors**
- `uv run python manage.py test` — full project suite passes

#### Manual Verification:

- In the browser (dev server): open the attraction list as an anonymous user, click Save on any attraction, arrive at the login page, click Register, complete the registration form, land on the attraction list, confirm the attraction is marked "Saved ✓"
- Confirm no existing login flow is broken: log out, click Save, log in with existing credentials, confirm the save completes

**Implementation Note**: Pause here for manual confirmation of both the automated green run and the manual browser walkthrough before marking this change complete.

---

## Testing Strategy

### Integration Tests

Five new tests across three classes in `attractions/tests.py`:

- `SaveAuthGateTest.test_anonymous_post_is_rejected` — Risk #2 core assertion
- `SaveAuthGateTest.test_authenticated_post_saves_and_redirects` — Risk #2 happy path anchor
- `SaveAuthGateTest.test_invalid_pk_returns_404` — 404 edge case
- `UserSaveIsolationTest.test_user_b_context_excludes_user_a_saves` — Risk #3 isolation
- `SaveAcrossAuthTest.test_login_path_save_persists` — Risk #1 login path
- `SaveAcrossAuthTest.test_register_path_save_persists` — Risk #1 register path (fails Phase 2, green Phase 3)

### Manual Testing Steps

1. Dev server running: `uv run python manage.py runserver`
2. Open browser as anonymous user, browse attractions, click Save on one
3. On the login page, click Register — verify the URL includes `?next=`
4. Complete registration with new credentials
5. Assert the attraction shows "Saved ✓" on the list page
6. Log out, repeat with Login (not Register) — verify same outcome

## References

- Research: `context/changes/testing-s02-critical-path/research.md`
- Test plan: `context/foundation/test-plan.md` §2 Risk Map, §3 Phase 1
- Existing test pattern: `attractions/tests.py:7` (`make_attraction` helper)
- Django auth redirect mechanism: `attractions/views.py:42-48` + comment

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Green tests (Risk #2 auth gate, Risk #3 user isolation, Risk #1 login path)

#### Automated

- [x] 1.1 `uv run python manage.py test attractions.tests.SaveAuthGateTest` — 3 tests, 0 failures — 4f8d576
- [x] 1.2 `uv run python manage.py test attractions.tests.UserSaveIsolationTest` — 1 test, 0 failures — 4f8d576
- [x] 1.3 `uv run python manage.py test attractions.tests.SaveAcrossAuthTest.test_login_path_save_persists` — 1 test, 0 failures — 4f8d576
- [x] 1.4 `uv run python manage.py test attractions` — 14 tests, 0 failures, 0 errors — 4f8d576

#### Manual

- [x] 1.5 5 new tests listed in output, all showing `.` (pass) — 4f8d576

### Phase 2: Red test (Risk #1 register path)

#### Automated

- [x] 2.1 `uv run python manage.py test attractions.tests.SaveAcrossAuthTest.test_register_path_save_persists` — 1 FAIL (AssertionError on DB row, not an error)
- [x] 2.2 `uv run python manage.py test attractions` — 15 tests, 14 pass, 1 fails, 0 errors

#### Manual

- [x] 2.3 Failure message names the missing `UserSavedAttraction` row

### Phase 3: Fix register-path bug

#### Automated

- [ ] 3.1 `uv run python manage.py test attractions.tests.SaveAcrossAuthTest.test_register_path_save_persists` — 1 test, 0 failures
- [ ] 3.2 `uv run python manage.py test attractions` — 15 tests, 0 failures, 0 errors
- [ ] 3.3 `uv run python manage.py test` — full project suite, 0 failures

#### Manual

- [ ] 3.4 Anonymous save → Register flow works end-to-end in the browser (attraction marked saved after registration)
- [ ] 3.5 Anonymous save → Login flow still works (no regression)

# S-02 Critical Path Tests — Plan Brief

> Full plan: `context/changes/testing-s02-critical-path/plan.md`
> Research: `context/changes/testing-s02-critical-path/research.md`

## What & Why

Write the Phase 1 Django integration tests from the test plan (Risks #1–#3: save-across-auth-redirect, server-side auth gate, user-scope isolation) and fix the confirmed register-path bug that research uncovered. Phase 1 of the test rollout cannot ship with a permanently failing test, so the fix and its proof land together in one change.

## Starting Point

`attractions/tests.py` has 11 tests covering only the browse/filter/HTMX list view — zero coverage of the save endpoint, auth redirect, or saved-pk isolation. The save and isolation code is correct; only the register path has a real bug.

## Desired End State

`uv run python manage.py test attractions` runs 15 tests and reports 0 failures. Five new tests prove each risk scenario. An anonymous user can click Save, complete registration, and find the attraction marked "Saved ✓" in the list — the bug is fixed.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Bug fix in scope | Yes — fix + tests in this change | Tests can't ship green without the fix; the two are the same user story | Plan |
| Phase order | Tests first (TDD) — green → red → green | Failing test documents the bug precisely before fix is applied | Plan |
| Test file | New classes in existing `attractions/tests.py` | Keeps one file per app; all tests use Attraction + UserSavedAttraction | Plan |
| Risk #1 test approach | Full redirect chain (`follow=True`) | Tests the exact failure scenario end-to-end; `force_login` shortcut wouldn't catch a broken `?next=` | Plan |
| Open-redirect validation | `url_has_allowed_host_and_scheme` required | Unvalidated `?next=` is an open-redirect vulnerability; Django ships the validator | Plan |
| Extra edge case | 404 on invalid pk | Verifies `get_object_or_404` is actually wired; cheap to add | Plan |
| Idempotency test | Not included | `unique_together` is the guarantee; not a risk-map item | Plan |

## Scope

**In scope:**
- 5 new tests in `attractions/tests.py` across 3 new classes
- Bug fix in `accounts/views.py` (read + validate `?next=` on successful register)
- Login template fix (`templates/registration/login.html` — forward `?next=` in Register link)
- Register template fix (`accounts/templates/accounts/register.html` — hidden `next` field)

**Out of scope:** HTMX regression guard (Phase 2), env/health tests (Phase 3), e2e browser automation, idempotency test, admin interface, migration tests.

## Architecture / Approach

The save-across-auth-redirect mechanism relies entirely on Django's `?next=` URL param — no session buffer, no middleware. `@login_required` appends the save URL as `next` on the 302 to login. Django's built-in login view reads it and redirects back; the custom register view currently ignores it. Fix: pass `next` through the template form → read from `request.POST` on success → validate → redirect.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Green tests | 5 tests all passing: auth gate (2), 404, user isolation, login-path save | Any of the 5 might reveal an unexpected gap in the existing code |
| 2. Red test | 1 failing test proves the register-path bug exactly | Test setup error (wrong credentials, wrong pk) could produce an error instead of an AssertionError — must distinguish |
| 3. Fix register bug | 3-file change turns Phase 2's test green; full suite 0 failures | Open-redirect validation must not break valid `next` URLs (same-host paths) |

**Prerequisites:** Dev environment working (`uv run python manage.py test` exits cleanly on the existing 11 tests).  
**Estimated effort:** ~1 session across 3 phases (tests are routine Django TestCase patterns; fix is ~15 lines across 3 files).

## Open Risks & Assumptions

- Phase 2's test must produce an `AssertionError` (wrong assertion), not a setup error — if the test errors out, the diagnostic value is lost. Watch the first run carefully.
- `url_has_allowed_host_and_scheme` in Django 6.0.5 accepts `allowed_hosts` as a set, not a string — use `{request.get_host()}`.
- The `next` value in test POST bodies is a raw path string (e.g. `/attractions/1/save/`) — no URL encoding needed in the test client; the view receives it as-is from `request.POST`.

## Success Criteria (Summary)

- `uv run python manage.py test attractions` exits 0 with 15 tests, 0 failures
- The register-path save flow works end-to-end in a manual browser test
- No regression on the existing login flow or any of the 11 pre-existing tests

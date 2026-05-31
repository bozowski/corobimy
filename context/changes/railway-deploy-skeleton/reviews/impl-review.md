<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Railway Deploy Skeleton

- **Plan**: context/changes/railway-deploy-skeleton/plan.md
- **Scope**: All phases (Phase 1 + Phase 2)
- **Date**: 2026-05-31
- **Verdict**: NEEDS ATTENTION (CRITICAL fixed during triage)
- **Findings**: 1 critical, 2 warnings, 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | FAIL (fixed) |
| Architecture | PASS |
| Pattern Consistency | WARNING (fixed) |
| Success Criteria | PASS |

## Findings

### F1 — Hardcoded SECRET_KEY fallback in production settings

- **Severity**: ❌ CRITICAL
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: corobimy/settings.py:24
- **Detail**: SECRET_KEY used os.environ.get() with a hardcoded django-insecure- fallback. If SECRET_KEY env var was absent, Django silently used the committed key to sign sessions, CSRF tokens, and password-reset links.
- **Fix**: Replaced .get() default with ImproperlyConfigured raise. Added `from django.core.exceptions import ImproperlyConfigured` import. Deployment now fails fast and visibly when the env var is missing.
- **Decision**: FIXED

### F2 — Unplanned ALLOWED_HOSTS hardcoded entry with uncertain hostname

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Scope Discipline
- **Location**: corobimy/settings.py:28
- **Detail**: Commit ec32c05 added `'healthcheck.railway.app'` hardcoded outside the plan. Potentially wrong hostname (Railway probes using service's own hostname). Unconditionally applied in all environments.
- **Fix A ⭐ Recommended**: Remove hardcoded entry; control via ALLOWED_HOSTS env var in Railway Variables dashboard.
  - Strength: Env-var-driven matches the rest of the settings file.
  - Tradeoff: Requires verifying exact Railway hostname before removing.
  - Confidence: MEDIUM
  - Blind spot: Current ALLOWED_HOSTS value in Railway Variables not checked.
- **Decision**: SKIPPED

### F3 — migrate coupled to start command risks mid-migration container kill

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: railway.toml:2
- **Detail**: python manage.py migrate runs inside startCommand. Plan explicitly accepted this risk for the skeleton phase. Already documented in infrastructure.md.
- **Fix**: No change needed now. When adding the first real model, use `railway run python manage.py migrate` as a pre-deploy step.
- **Decision**: SKIPPED

### F4 — Health endpoint responds to all HTTP methods

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: corobimy/views.py:4–5
- **Detail**: Health view had no method guard; returned 200 for GET, POST, DELETE, etc.
- **Fix**: Added `@require_GET` decorator from `django.views.decorators.http`.
- **Decision**: FIXED

### F5 — Test uses hardcoded URL string instead of reverse()

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: corobimy/tests.py:7
- **Detail**: `self.client.get('/health/')` used a hardcoded string rather than `reverse('health')`.
- **Fix**: Replaced with `self.client.get(reverse('health'))`, added `from django.urls import reverse` import.
- **Decision**: FIXED

<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: S-02 Critical Path Tests

- **Plan**: context/changes/testing-s02-critical-path/plan.md
- **Scope**: All Phases (1, 2, 3)
- **Date**: 2026-06-12
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical  0 warnings  3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Findings

### F1 — Unplanned conftest.py + pyproject.toml additions

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: conftest.py:1-6, pyproject.toml
- **Detail**: Two benign test-infrastructure files added outside the plan. conftest.py injects SECRET_KEY/DEBUG for pytest; pyproject.toml adds pytest + mutmut config. Neither touches app code. Gap: conftest.py's pytest_configure fires too late — SECRET_KEY must be set in the environment before pytest starts.
- **Fix**: Append an addendum to plan.md documenting these two files.
- **Decision**: FIXED — addendum appended to plan.md

### F2 — next preserved via GET query string only — brittle outside browser flows

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: accounts/views.py:20
- **Detail**: On failed registration POST, view re-renders with `request.GET.get('next', '')`. Plan-consistent and correct in browser flow (?next= stays in URL). Would silently drop next if POSTed directly without ?next= in URL.
- **Fix**: `'next': request.POST.get('next', '') or request.GET.get('next', '')`
- **Decision**: SKIPPED

### F3 — Hardcoded URL strings in SaveAcrossAuthTest

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: attractions/tests.py:165, 185
- **Detail**: `/accounts/login/` and `/accounts/register/` hardcoded; every sibling test class uses `reverse()`.
- **Fix**: Replace with `reverse('login')` and `reverse('register')`.
- **Decision**: FIXED — attractions/tests.py updated; 19/19 tests still green

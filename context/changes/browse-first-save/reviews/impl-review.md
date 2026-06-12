<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Browse-first Save

- **Plan**: context/changes/browse-first-save/plan.md
- **Scope**: All 4 phases
- **Date**: 2026-06-12
- **Verdict**: NEEDS ATTENTION (fixed during triage)
- **Findings**: 0 critical, 3 warnings, 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Findings

### F1 — save_attraction accepts all HTTP methods

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: attractions/views.py:38
- **Detail**: The plan explicitly requires no method restriction because Django's @login_required ?next= mechanism redirects as a GET after login. However, GET carries no CSRF token, so any authenticated user following a plain link to /attractions/5/save/ will silently create a save record.
- **Fix A ⭐ Applied**: Added a comment documenting the GET requirement and the get_or_create idempotency guarantee.
- **Decision**: FIXED via Fix A

### F2 — saved_pks is an unbounded per-request query

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: attractions/views.py:18
- **Detail**: SELECT attraction_id FROM usersavedattraction WHERE user_id=X fetches all saved PKs on every request, growing linearly with a user's save history.
- **Fix**: Scoped saved_pks query to page_pks (attraction_id__in=page_pks), bounding it to PAGE_SIZE rows.
- **Decision**: FIXED

### F3 — save redirects to hardcoded '/'

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: attractions/views.py:44
- **Detail**: return redirect('/') uses a magic string that will break if the root URL ever changes.
- **Fix**: Replaced with redirect('attraction-list').
- **Decision**: FIXED

### F4 — Load-more only forwards category; future filters silently dropped

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: attractions/templates/attractions/partials/filter_results.html:16
- **Detail**: HTMX Load More button manually threads ?category= into the URL. Pre-existing issue. Any future filter field will be silently dropped on pagination.
- **Fix**: No code change. Lesson recorded in context/foundation/lessons.md: "HTMX pagination must forward all active filter params".
- **Decision**: ACCEPTED-AS-RULE: HTMX pagination must forward all active filter params

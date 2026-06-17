<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Unsave Attraction (S-06)

- **Plan**: `context/changes/unsave-attraction/plan.md`
- **Scope**: Full plan (Phase 1 + Phase 2 of 2)
- **Date**: 2026-06-18
- **Verdict**: APPROVED
- **Findings**: 0 critical | 1 warning | 3 observations

## Verdicts

| Dimension | Verdict |
|---|---|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

**Note on CSRF investigation**: Safety agent flagged CSRF on the HTMX unsave button as CRITICAL. Investigated and cleared — `base.html:10` sets `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` on `<body>`, which HTMX inherits for all descendant requests. The swapped-in partial is always within that `<body>` scope.

## Findings

### F1 — unsave_attraction performs deletion on GET requests

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: `attractions/views.py:53–65`
- **Detail**: The view deleted on any authenticated request. Unlike `save_attraction` (which needs GET for the `?next=` redirect), `unsave_attraction` has no such requirement — only reached via `hx-post`. A logged-in user following a crafted GET link would silently delete their save.
- **Fix**: Added `@require_POST` above `@login_required` on `unsave_attraction`.
  - Strength: One-line fix; aligns with `UnsaveViewTest` (all POST). No existing callers use GET.
  - Tradeoff: Anonymous GET now returns 405 instead of 302 to login — negligible since anonymous users can't see the button.
  - Confidence: HIGH
  - Blind spot: None significant.
- **Decision**: FIXED

### F2 — hardcoded saved_pks=set() is an undocumented design constraint

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: `attractions/views.py:60–64`
- **Detail**: `unsave_attraction` passes `saved_pks=set()` to drive `save_button.html` into its "Save" branch. Correct for single-attraction scope but undocumented.
- **Fix**: Added inline comment: `# empty → partial renders the Save branch`
- **Decision**: FIXED

### F3 — extra test test_non_htmx_post_redirects_to_list beyond plan

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: `attractions/tests.py:197–201`
- **Detail**: A 6th test added beyond the 5 planned. Covers the non-HTMX redirect fallback. Useful, additive, no problems.
- **Decision**: SKIPPED (welcome coverage, no action needed)

### F4 — pre-existing lessons.md violation in Load More buttons

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: `filter_results.html:29`, `cards_append.html:23`
- **Detail**: Load More buttons thread `?category=` manually, violating the lessons.md rule. Pre-existing debt, not introduced by this change.
- **Decision**: SKIPPED (handle in a separate task)

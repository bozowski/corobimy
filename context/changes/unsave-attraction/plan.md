# Unsave Attraction (S-06) Implementation Plan

## Overview

Implement the unsave action (S-06): a logged-in user who has previously saved an attraction can click "Saved ✓" on the card to remove the save in place, with HTMX swapping the button back to "Save" without a full page reload.

## Current State Analysis

The `browse-first-save` change (S-02) is fully shipped. The relevant foundation:

- `UserSavedAttraction` model at `attractions/models.py:25–35` — join table with `unique_together = [('user', 'attraction')]`
- `save_attraction` view at `attractions/views.py:43–49` — `@login_required`, `get_or_create`, redirects to `attraction-list`
- `saved_pks` computed in `attraction_list` at `views.py:19–27` — scoped to the page's PKs, passed to all three render paths
- Both card templates render "Saved ✓" as a **static `<span>`** — nothing clickable today
- `base.html:10` sets `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` on `<body>` — HTMX POSTs carry CSRF automatically
- `django-htmx` middleware is wired in (`request.htmx` is available in views)

### Key Discoveries

- `filter_results.html` and `cards_append.html` share identical inline save/saved logic — extracting to a shared partial eliminates the duplication
- The `{% include %}` tag in Django passes the parent context by default — `attraction` (loop variable) and `saved_pks` are available in the partial without explicit `with` args
- When the partial is rendered directly by the unsave view (HTMX response), `saved_pks` must be passed explicitly as an empty set to drive the "Save" branch
- The CSRF form tag in the partial works in both contexts: `{% include %}` inherits context processors; `render(request, ...)` fires them too

## Desired End State

A logged-in user who has saved an attraction sees "Saved ✓" on the card as a clickable button. Clicking it sends an HTMX POST to the new `/attractions/<pk>/unsave/` endpoint; the server deletes the `UserSavedAttraction` row and returns the "Save" button fragment; HTMX swaps it in place — no page reload. The "Save" button still works as before (plain POST + redirect).

### Verification

- Authenticated user clicks "Saved ✓" → button swaps to "Save" in place; `UserSavedAttraction` row is gone from DB
- Double-click / stale-tab scenario: POST to unsave when already unsaved → 200, Save button returned, no error
- Anonymous user cannot reach the unsave endpoint; `@login_required` blocks the request
- "Save" button still works: plain POST → row created → redirect → page reloads showing "Saved ✓"

## What We're NOT Doing

- HTMX enhancement for the save button (save stays plain POST + redirect; only unsave uses HTMX)
- A "Saved attractions" list page
- Undo / redo history
- Confirmation dialog before unsaving
- In-place "Save" → row created without page reload (separate enhancement)

## Implementation Approach

Two phases in dependency order: backend first (view + URL, independently testable via HTTP), then frontend (partial extraction + HTMX wiring).

The "Saved ✓" button uses HTMX (`hx-post`, `hx-target="#save-btn-<pk>"`, `hx-swap="innerHTML"`). CSRF is carried automatically via the `hx-headers` on `<body>`. The unsave view checks `request.htmx` and returns the fragment on HTMX requests; for any non-HTMX hit (e.g., direct URL navigation) it redirects to `attraction-list` as a safe fallback.

---

## Phase 1: Unsave View and URL

### Overview

Add the `unsave_attraction` view and URL pattern. The view deletes the save row (idempotent via `.filter().delete()`), then returns the `save_button.html` fragment for HTMX or redirects for non-HTMX. The `save_button.html` partial does not yet exist — the view renders it first; the template is created in this phase as a standalone file before Phase 2 wires it into the card templates.

### Changes Required

#### 1. Add `unsave_attraction` view

**File**: `attractions/views.py`

**Intent**: Handle unsave requests for authenticated users. Deletes the save row if it exists (silently succeeds if not). Returns the save-button fragment for HTMX; redirects to browse for direct URL hits.

**Contract**:
- Decorated with `@login_required`
- `attraction = get_object_or_404(Attraction, pk=pk)` — 404 on invalid pk
- `UserSavedAttraction.objects.filter(user=request.user, attraction=attraction).delete()` — idempotent
- `if request.htmx:` → `render(request, 'attractions/partials/save_button.html', {'attraction': attraction, 'saved_pks': set()})`
- `else:` → `redirect('attraction-list')`

#### 2. Add unsave URL pattern

**File**: `attractions/urls.py`

**Intent**: Route POST (and fallback GET) requests to the unsave view.

**Contract**: `path('attractions/<int:pk>/unsave/', views.unsave_attraction, name='attraction-unsave')` added after the existing save pattern.

#### 3. Create `save_button.html` partial (stub)

**File**: `attractions/templates/attractions/partials/save_button.html` (new file)

**Intent**: Render either the "Saved ✓" HTMX trigger or the plain "Save" form, based on whether `attraction.pk in saved_pks`. This partial is the single source of truth for the save/unsave button state.

**Contract**:
- `{% if attraction.pk in saved_pks %}` branch:
  - `<button>` element (not a form) with `hx-post="{% url 'attraction-unsave' attraction.pk %}"`, `hx-target="#save-btn-{{ attraction.pk }}"`, `hx-swap="innerHTML"`, `type="button"`
  - Label: `Saved ✓`; styling: green, cursor-pointer, hover effect (e.g., `hover:line-through` or `hover:text-green-800`)
- `{% else %}` branch:
  - Exact form + button from the current `filter_results.html:11–18` (unchanged styling)
  - Includes `{% csrf_token %}`

#### 4. Add `UnsaveViewTest` tests

**File**: `attractions/tests.py`

**Intent**: Cover the unsave view's auth gate, deletion behavior, idempotency, and HTMX response content.

**Contract**: New `UnsaveViewTest(TestCase)` class with `setUpTestData` creating one attraction, one user, and one `UserSavedAttraction`. Test methods:
- `test_anonymous_post_redirects_to_login`: anonymous POST → 302, location contains `/accounts/login/`, row still exists
- `test_authenticated_post_deletes_save`: force-login, POST with `HTTP_HX_REQUEST='true'` → 200, `UserSavedAttraction` row gone
- `test_invalid_pk_returns_404`: force-login, POST to non-existent pk → 404
- `test_unsave_when_not_saved_is_idempotent`: force-login, DELETE the row first, then POST → 200, no error raised
- `test_htmx_response_contains_save_button`: force-login, POST with HTMX header → response HTML contains `attraction-save` URL (the Save form action)

### Success Criteria

#### Automated Verification

- `uv run python manage.py check` — no issues
- `uv run python manage.py test` — all existing tests plus the new `UnsaveViewTest` pass

#### Manual Verification

- `POST /attractions/1/unsave/` (HTMX header) while logged in → response body is the "Save" form fragment; DB row is gone
- `POST /attractions/1/unsave/` (HTMX header) when not saved → 200, "Save" form returned (no error page)
- Anonymous POST → 302 to `/accounts/login/?next=/attractions/1/unsave/`
- `GET /attractions/99999/unsave/` while logged in → 404

**Implementation Note**: After completing Phase 1 and all automated verification passes, pause for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Save Button Partial — Template Wiring

### Overview

Replace the duplicated inline save/saved logic in both card templates with `{% include "attractions/partials/save_button.html" %}`. Add `id="save-btn-{{ attraction.pk }}"` to the wrapper `<div>` in each template so the HTMX target resolves correctly.

### Changes Required

#### 1. Update `filter_results.html`

**File**: `attractions/templates/attractions/partials/filter_results.html`

**Intent**: Add the HTMX target ID to the button wrapper and replace the inline save/saved logic with the shared partial.

**Contract**:
- Change `<div class="mt-3">` to `<div class="mt-3" id="save-btn-{{ attraction.pk }}">`
- Replace the existing `{% if attraction.pk in saved_pks %}...{% endif %}` block with `{% include "attractions/partials/save_button.html" %}`
- No other changes

#### 2. Update `cards_append.html`

**File**: `attractions/templates/attractions/partials/cards_append.html`

**Intent**: Mirror the same wrapper ID and include pattern for cards loaded via HTMX load-more.

**Contract**: Identical change to `filter_results.html` — add `id="save-btn-{{ attraction.pk }}"` to `<div class="mt-3">` and replace inline logic with `{% include "attractions/partials/save_button.html" %}`.

### Success Criteria

#### Automated Verification

- `uv run python manage.py test` — all tests pass (including existing HTMX partial tests and new `UnsaveViewTest`)
- `uv run python manage.py check` — no issues

#### Manual Verification

- Browse page: "Saved ✓" renders as a clickable element on saved attraction cards
- Click "Saved ✓" → HTMX swaps button to "Save" in place, no page reload; `UserSavedAttraction` row deleted from DB
- Click the swapped-in "Save" button → plain POST → page reloads → card shows "Saved ✓" again
- Load-more (HTMX append): newly loaded cards show correct button state
- Filter (HTMX swap): filtered results show correct button state
- No regression in filter, load-more, empty state, or category display

**Implementation Note**: After completing Phase 2 and all automated verification passes, pause for full manual confirmation of the unsave flow before declaring this change complete.

---

## Testing Strategy

### New Tests (Phase 1)

`UnsaveViewTest` in `attractions/tests.py`:
- Auth gate (anonymous → redirect)
- Deletion behavior (authenticated → row gone)
- Idempotency (unsave when not saved → 200, no error)
- Invalid pk → 404
- HTMX response content (contains the Save form)

### Existing Tests That Must Keep Passing

All tests in `attractions/tests.py` and `corobimy/tests.py` — particularly `AttractionListViewTest` (HTMX partial tests) which exercise `filter_results.html` and `cards_append.html` directly. The template refactor (Phase 2) is the highest-regression risk.

### Manual Testing Steps

1. Start dev server: `uv run python manage.py runserver`
2. Log in as a user who has at least one saved attraction
3. Browse to `/` — verify "Saved ✓" appears as a clickable button on saved cards
4. Click "Saved ✓" — verify the button swaps to "Save" without a page reload; check DB row is gone
5. Click "Save" on the same card — verify plain POST + redirect; card shows "Saved ✓" again
6. Load more attractions — verify correct button state on newly appended cards
7. Filter by category — verify correct button state on filtered results
8. Open a second session as a different user — verify their save state is independent

## References

- Parent plan: `context/changes/browse-first-save/plan.md`
- `attractions/models.py:25–35` — `UserSavedAttraction` model
- `attractions/views.py:43–49` — `save_attraction` view (pattern to mirror for unsave)
- `attractions/templates/attractions/partials/filter_results.html` — primary card template
- `attractions/templates/attractions/partials/cards_append.html` — load-more card template
- `templates/base.html:10` — `hx-headers` CSRF pattern (HTMX POSTs carry CSRF automatically)

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Unsave View and URL

#### Automated

- [x] 1.1 System check passes (`uv run python manage.py check`) — bd8dbf4
- [x] 1.2 All tests pass including new `UnsaveViewTest` (`uv run python manage.py test`) — bd8dbf4

#### Manual

- [x] 1.3 Authenticated HTMX POST to `/attractions/1/unsave/` returns Save form fragment; DB row deleted — bd8dbf4
- [x] 1.4 Idempotent: HTMX POST when not saved → 200, Save form returned — bd8dbf4
- [x] 1.5 Anonymous POST → 302 to `/accounts/login/?next=...` — bd8dbf4
- [x] 1.6 Invalid pk → 404 — bd8dbf4

### Phase 2: Save Button Partial — Template Wiring

#### Automated

- [x] 2.1 All tests pass (`uv run python manage.py test`) — 5492ad5
- [x] 2.2 System check passes (`uv run python manage.py check`) — 5492ad5

#### Manual

- [x] 2.3 "Saved ✓" renders as a clickable button on saved cards — 5492ad5
- [x] 2.4 Click "Saved ✓" → in-place HTMX swap to "Save" button; DB row gone — 5492ad5
- [x] 2.5 Click "Save" (after unsave) → plain POST + redirect; card shows "Saved ✓" again — 5492ad5
- [x] 2.6 Load-more cards show correct button state — 5492ad5
- [x] 2.7 Filter (HTMX swap) shows correct button state — 5492ad5
- [x] 2.8 No regression in filter, load-more, empty state, or category display — 5492ad5

# Unsave Attraction (S-06) — Plan Brief

> Full plan: `context/changes/unsave-attraction/plan.md`

## What & Why

Add the ability for a logged-in user to remove a previously saved attraction (S-06). Currently "Saved ✓" is a static span — clicking it does nothing. This change makes it a clickable HTMX button that deletes the save in place without a full page reload.

## Starting Point

`browse-first-save` (S-02) is fully shipped: `UserSavedAttraction` model, `save_attraction` view, `saved_pks` context, and "Saved ✓" span in both card templates all exist. The only missing piece is the inverse action and the HTMX wiring to make "Saved ✓" interactive.

## Desired End State

A logged-in user who has saved an attraction sees "Saved ✓" as a clickable button on the card. Clicking it POSTs to `/attractions/<pk>/unsave/` via HTMX; the server deletes the save row and returns the "Save" button fragment; HTMX swaps it in — the card updates instantly. The "Save" button continues to work via plain POST + redirect (unchanged).

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
|---|---|---|
| Unsave trigger UX | "Saved ✓" is the clickable button | Zero extra elements; the indicator IS the action |
| Interaction model | HTMX in-place swap | No full page reload on unsave; save can stay plain POST |
| Edge case (not saved) | Silently succeed (`.filter().delete()`) | Matches the save side's `get_or_create` idempotency |
| Confirmation | None — immediate action | Low stakes; user can always re-save with one click |
| Non-HTMX fallback | Redirect to `attraction-list` | Safe fallback for direct URL navigation |

## Scope

**In scope:**
- `unsave_attraction` view + URL (`/attractions/<pk>/unsave/`, name `attraction-unsave`)
- `save_button.html` shared partial (eliminates the duplicated inline logic in both card templates)
- `id="save-btn-{{ attraction.pk }}"` on the button wrapper div in both card templates
- `UnsaveViewTest` test class covering auth gate, deletion, idempotency, 404, HTMX response

**Out of scope:**
- HTMX enhancement for the save button (stays plain POST + redirect)
- "Saved attractions" list page
- Confirmation dialog
- In-place save without page reload

## Architecture / Approach

The "Saved ✓" button uses HTMX attributes (`hx-post`, `hx-target="#save-btn-<pk>"`, `hx-swap="innerHTML"`). CSRF is carried automatically via the existing `hx-headers` on `<body>`. The unsave view branches on `request.htmx`: returns the `save_button.html` fragment for HTMX requests, redirects to browse for direct navigation. The partial renders both states (`saved` / `unsaved`) and is the single source of truth — replacing duplicated inline logic in `filter_results.html` and `cards_append.html`.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Unsave View and URL | Working unsave endpoint + `save_button.html` partial + `UnsaveViewTest` | None significant — purely additive |
| 2. Template Wiring | "Saved ✓" clickable in both card templates; inline logic replaced by `{% include %}` | Existing HTMX partial tests (`AttractionListViewTest`) could catch regressions in the refactor |

**Prerequisites:** `browse-first-save` fully merged (it is).
**Estimated effort:** ~1 session across 2 small phases.

## Open Risks & Assumptions

- `django-htmx` is installed and `request.htmx` is available in views — assumed from the existing load-more implementation.
- The `hx-headers` CSRF on `<body>` covers HTMX POSTs — confirmed from `base.html:10`; no additional CSRF wiring needed.

## Success Criteria (Summary)

- Clicking "Saved ✓" on a saved card swaps the button to "Save" in place (HTMX, no reload); DB row is deleted.
- Double-clicking or hitting the unsave URL on an already-unsaved attraction returns 200 with the Save button (no error).
- All existing tests continue to pass; new `UnsaveViewTest` passes.

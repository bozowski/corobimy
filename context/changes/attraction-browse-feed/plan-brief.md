# Attraction Browse Feed — Plan Brief

> Full plan: `context/changes/attraction-browse-feed/plan.md`
> Research: `context/changes/attraction-browse-feed/research.md`

## What & Why

Build S-01: an anonymous browse-and-filter feed of Kraków attractions. Users open the app at `/`, see a card grid with a category filter (family / couples / sport / culture), and can narrow results with instant HTMX filtering and a load-more button. This is the prerequisite for every other slice — S-02 auth and S-03 content refresh both build on this feed existing.

## Starting Point

The codebase is a clean Django 6.0.5 skeleton: `django-filter` and `django-htmx` are not yet installed, no `attractions/` app exists, no templates or models are present, and the root URL (`/`) returns 404. The Railway deploy pipeline (F-01) is live and healthy.

## Desired End State

A visitor opens `/` and sees "Discover Kraków" with six attraction cards (alphabetical order). Selecting a category from the dropdown instantly swaps the grid via HTMX with no page reload. In the unfiltered view (12 attractions), a "Load more" button appends the next six. Each filtered category shows its three results with no load-more button. No authentication required.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Root URL | `/` (root) | Attractions list IS the homepage — no redirect needed for MVP | Plan |
| Persona / default sort | Local (alphabetical, "Discover Kraków" copy) | Roadmap open question resolved for local discovery audience | Plan |
| Pagination | HTMX load-more, PAGE_SIZE=6 | Meaningful load-more flow even with 12 seeds; infinite-scroll preferred over numbered pages | Plan |
| Base template location | Project-level `templates/base.html` | S-02 auth pages must extend the same base; app-level would require duplication | Plan |
| Seed data | 12 real Kraków attractions, 3 per category, written in plan | Feed must be non-empty and cover all four filter states for demo and QA | Plan |
| Libraries | django-filter 25.2 + django-htmx + Tailwind CDN | All confirmed compatible with Django 6.0.5 + Python 3.13; no conflicts | Research |
| App location | Repo root, created with `startapp` | AGENTS.md hard rule: feature apps are siblings of `manage.py`, not inside `corobimy/` | Research |
| Migrations | Trivial CREATE TABLE only; seed data via `loaddata` | Migrations coupled to Railway startup; RunPython in migration risks timeout | Research |

## Scope

**In scope:**
- `attractions/` Django app: `Attraction` model, `AttractionFilter`, `attraction_list` view
- Three templates: `list.html`, `filter_results` partial, `cards_append` partial
- Project-level `templates/base.html` with Tailwind CDN + HTMX script
- 12-entry fixture + `loaddata` step
- Tests: model, view (3 modes), FilterSet

**Out of scope:**
- Authentication, save, or bookmark features (S-02)
- Operator content refresh (S-03)
- Pagination via page numbers
- Custom CSS, Sass, or Node build pipeline
- AI-assisted or scraped content

## Architecture / Approach

One Django app (`attractions/`), one view (`attraction_list`), one URL (`/`). The view dispatches on `request.htmx` and `offset`:

- **Full page** (`request.htmx` is falsy): renders `list.html` with filter form and first 6 cards
- **Category change** (`request.htmx` + `offset == 0`): renders `filter_results.html` — replaces `#filter-results` with `innerHTML` swap
- **Load-more** (`request.htmx` + `offset > 0`): renders `cards_append.html` — appends to `#attraction-grid` with `beforeend` + OOB-replaces `#load-more-container`

`#load-more-container` must be a sibling of `#attraction-grid` (not nested inside it) for the OOB pattern to work correctly.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Dependencies + Settings + Base Template | `uv add`, settings wired, `base.html` created | `collectstatic` fails if HTMX static file not collected |
| 2. Attraction App + Data Model | `startapp`, model, migration, admin | Migration timeout on Railway (trivial migration, should be <5 s) |
| 3. Browse View + Filter + URL Routing + Templates | Full working browse + filter + HTMX load-more at `/` | OOB swap pattern broken if `#load-more-container` is nested in grid |
| 4. Seed Data | 12 real Kraków attractions loaded, all four filter states non-empty | `loaddata` on Railway requires a public Postgres URL or Railway SSH |
| 5. Tests | Regression baseline for model, view, filter | HTMX header in Django test client requires `HTTP_HX_REQUEST='true'` kwarg |

**Prerequisites:** F-01 done (Railway live, Postgres wired, health check passing) ✓
**Estimated effort:** ~2-3 dev sessions across 5 phases

## Open Risks & Assumptions

- Railway `loaddata` step for seed data requires access to production Postgres (public URL or `railway run`). If unavailable at deploy time, seed data must be loaded separately before demo.
- Tailwind CDN Play (`https://cdn.tailwindcss.com`) is a development-grade CDN — acceptable for MVP; will need to be replaced with a proper PostCSS build or CDN pin before production at scale.
- OOB swap correctness depends on maintaining the `#attraction-grid` / `#load-more-container` sibling structure. A template restructuring that nests the container inside the grid will silently break load-more.

## Success Criteria (Summary)

- `GET /` returns the attraction list to anonymous users with no authentication prompt
- Category filter changes update the card grid via HTMX with no full page reload
- "Load more" appends remaining cards and removes itself when all items are shown

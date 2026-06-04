# Attraction Browse Feed — Implementation Plan (S-01)

## Overview

Build S-01 from scratch: a new `attractions/` Django app that lets anonymous users browse and filter 12 seeded Kraków attractions by category (family / couples / sport / culture) with instant HTMX category filtering and a load-more button for unpaged browsing. No auth required. Deployed to Railway on merge.

## Current State Analysis

The codebase is a clean Django 6.0.5 skeleton with no feature apps. What exists:

- `corobimy/settings.py` — settings wired: DjangoTemplates (`APP_DIRS=True`), WhiteNoise, dj-database-url (PostgreSQL on Railway, SQLite locally), CSRF middleware, logging
- `corobimy/urls.py` — only `/admin/` and `/health/` wired; no root path
- `corobimy/views.py` — health check only
- `pyproject.toml` — Django 6.0.5, Python 3.13, whitenoise, psycopg, gunicorn; `django-filter` and `django-htmx` absent
- No `attractions/` app, no templates directory, no static files, no models

Libraries confirmed compatible with Django 6.0.5 + Python 3.13: `django-filter` 25.2, `django-htmx`, HTMX (via `{% htmx_script %}`), Tailwind CDN. See `context/changes/attraction-browse-feed/research.md` for verdicts.

Key code references:
- `corobimy/settings.py:36-43` — INSTALLED_APPS to extend
- `corobimy/settings.py:45-54` — MIDDLEWARE (HtmxMiddleware goes after line 47)
- `corobimy/settings.py:58-71` — TEMPLATES (add `BASE_DIR / 'templates'` to DIRS)
- `corobimy/urls.py:21-24` — existing URL patterns to extend

## Desired End State

A visitor opens the app at `/` and sees a "Discover Kraków" heading with a category filter select. Six attraction cards appear (alphabetical order — local discovery persona). Selecting a category instantly swaps the card grid via HTMX without a page reload. In the unfiltered view (12 attractions), a "Load more" button appends the next six cards. Each filtered category shows its three attractions on one screen with no load-more button. No authentication required at any point.

### Key Discoveries

- `APP_DIRS=True` → `attractions/templates/` is auto-discovered without editing `TEMPLATES['DIRS']`. Adding `BASE_DIR / 'templates'` to DIRS is needed for the project-level `corobimy/templates/base.html` only.
- AGENTS.md hard rule: feature code must NOT live in `corobimy/`. Create `attractions/` app at repo root with `uv run python manage.py startapp attractions`.
- Migrations are coupled to gunicorn start (`railway.toml`). The first `Attraction` migration must be trivial — no `RunPython`, no data transforms.
- `django.template.context_processors.request` is already in `TEMPLATES['OPTIONS']['context_processors']` (`settings.py:65`), so `request` is available in all templates. The load-more button template can reference `request.GET.category` directly.
- HTMX's `{% htmx_script %}` tag (from django-htmx) serves HTMX via WhiteNoise/static files — no separate CDN script needed.
- CATEGORY_CHOICES are fixed by domain contract (AGENTS.md + PRD): `family`, `couples`, `sport`, `culture`. Do not add or rename categories.

## What We're NOT Doing

- Pagination via page numbers — load-more only; `PAGE_SIZE = 6`
- Tourist-oriented copy or ordering — local persona, alphabetical default sort
- Any authentication, saved attractions, or user accounts (S-02)
- A separate landing page at `/` — attractions list IS the homepage
- Automated scraping or AI categorisation (S-03)
- Custom CSS or a Node build pipeline — Tailwind CDN only
- Deployment of seed data via data migration — `loaddata` only

## Implementation Approach

Five sequential phases: install dependencies and wire settings → scaffold the data layer → build the browse/filter/HTMX view and templates → load seed data → add tests. Each phase has automated and manual success criteria; pause for manual confirmation before the next phase.

The HTMX pattern uses two response modes inside `attraction_list`:
- **Category filter change**: form sends `hx-target="#filter-results"` with `innerHTML` swap — the entire results section (grid + load-more button) is replaced, offset resets to 0 implicitly.
- **Load-more**: button sends `hx-target="#attraction-grid"` with `beforeend` swap — new cards are appended, and `#load-more-container` is updated via HTMX OOB swap.

## Critical Implementation Details

**OOB swap requires `#load-more-container` to be a sibling of `#attraction-grid`, not a child.** If it is nested inside the grid, the `beforeend` swap for load-more will duplicate the button inside the cards. Keep the DOM structure:

```
#filter-results
  #attraction-grid   ← cards appended here on load-more
  #load-more-container  ← OOB-replaced on load-more; fully replaced with #filter-results on category change
```

**`hx-swap-oob` is an attribute on the OOB element in the response, not in the HTML page.** `cards_append.html` must include `<div id="load-more-container" hx-swap-oob="true">...</div>` as a sibling of the new card HTML, not as a nested child.

---

## Phase 1: Dependencies + Settings + Base Template

### Overview

Install `django-filter` and `django-htmx`, wire them into settings, add the project-level templates directory, and create `base.html` with Tailwind CDN and the HTMX script tag. After this phase the Django server starts cleanly and the base template is renderable.

### Changes Required

#### 1. Install packages

**File**: `pyproject.toml` (via shell command, not direct edit)

**Intent**: Add `django-filter` and `django-htmx` to project dependencies so they are available in both local dev and Railway deploys.

**Contract**: Run `uv add django-filter django-htmx`. This updates `[project].dependencies` in `pyproject.toml` and regenerates `uv.lock`. Commit both files.

#### 2. Wire INSTALLED_APPS

**File**: `corobimy/settings.py:43`

**Intent**: Register `django_filters` and `django_htmx` as installed apps so their template tags, static files, and management commands are available.

**Contract**: Append `'django_filters'` and `'django_htmx'` to the `INSTALLED_APPS` list after the existing six Django contrib apps.

#### 3. Wire HtmxMiddleware

**File**: `corobimy/settings.py:48`

**Intent**: Enable `request.htmx` on every request so views can branch on HTMX vs full-page responses.

**Contract**: Insert `'django_htmx.middleware.HtmxMiddleware'` between `WhiteNoiseMiddleware` (line 47) and `SessionMiddleware` (line 48).

#### 4. Add project-level templates directory

**File**: `corobimy/settings.py:61`

**Intent**: Allow `base.html` to live in `corobimy/templates/` (project-level) so S-02 auth pages can extend the same base. App templates in `attractions/templates/` are already discovered via `APP_DIRS=True`.

**Contract**: Change `'DIRS': []` to `'DIRS': [BASE_DIR / 'templates']`. Create the directory `corobimy/templates/` (the directory under the repo root, not inside the `corobimy/` package — i.e., the directory lives at `<repo_root>/templates/`).

Wait — `BASE_DIR` in `settings.py` is the repo root (the directory containing `manage.py`). So `BASE_DIR / 'templates'` = `<repo_root>/templates/`. This is correct.

#### 5. Create base template

**File**: `templates/base.html` (at repo root, not inside `corobimy/`)

**Intent**: Provide the HTML shell that all feature pages extend — loads Tailwind CDN for utility classes and `{% htmx_script %}` for HTMX.

**Contract**: New file. Must contain:
- `{% load django_htmx %}` before the `<html>` tag
- `<script src="https://cdn.tailwindcss.com"></script>` in `<head>`
- `<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>` — forwards CSRF token on all HTMX POST requests
- `{% htmx_script %}` immediately after the opening `<body>` tag
- `{% block title %}Discover Kraków{% endblock %}` in `<title>`
- `{% block content %}{% endblock %}` in the body

### Success Criteria

#### Automated Verification

- `uv run python manage.py check` exits 0 with no errors
- `uv run python manage.py collectstatic --no-input` exits 0 (HTMX static file collected)

#### Manual Verification

- Dev server starts: `uv run python manage.py runserver`
- No import errors in the terminal
- `/health/` still returns `{"status": "ok"}`
- `/admin/` still loads

**Implementation Note**: Pause here for manual confirmation before Phase 2.

---

## Phase 2: Attraction App + Data Model

### Overview

Create the `attractions` Django app at repo root, define the `Attraction` model, generate and apply the initial migration, and register the model in the admin. After this phase an attraction can be created manually via `/admin/`.

### Changes Required

#### 1. Create the app

**File**: repo root (shell command)

**Intent**: Scaffold the attractions app directory structure using Django's management command, as required by AGENTS.md (feature apps created with `startapp`, placed at repo root).

**Contract**: Run `uv run python manage.py startapp attractions`. This creates `attractions/` as a sibling of `manage.py` with `models.py`, `views.py`, `admin.py`, `apps.py`, `tests.py`, and `migrations/`.

#### 2. Define the Attraction model

**File**: `attractions/models.py`

**Intent**: Represent a single Kraków attraction with its category, name, and description. Default ordering is alphabetical to match the local discovery persona.

**Contract**: Replace the default file content. The model needs:
- `CATEGORY_CHOICES`: list of 2-tuples matching the four locked domain values (`'family'`/`'Families'`, `'couples'`/`'Couples'`, `'sport'`/`'Sport'`, `'culture'`/`'Culture'`)
- `name = models.CharField(max_length=200)`
- `category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)`
- `description = models.TextField()`
- `created_at = models.DateTimeField(auto_now_add=True)`
- `class Meta: ordering = ['name']`
- `__str__` returning `self.name`

`CATEGORY_CHOICES` should be defined at module level so `attractions/filters.py` can import it without importing the model class.

#### 3. Register the app in INSTALLED_APPS

**File**: `corobimy/settings.py:43`

**Intent**: Make Django aware of the attractions app so migrations, template discovery, and static files work.

**Contract**: Append `'attractions.apps.AttractionsConfig'` to `INSTALLED_APPS` after `'django_htmx'`.

#### 4. Generate and apply migration

**File**: `attractions/migrations/0001_initial.py` (generated)

**Intent**: Produce the database schema for `Attraction` and commit it alongside the model change.

**Contract**: Run `uv run python manage.py makemigrations attractions` then `uv run python manage.py migrate`. Commit the generated migration file in the same change.

#### 5. Register in admin

**File**: `attractions/admin.py`

**Intent**: Allow manual creation and editing of attractions via `/admin/` during development and for operator use.

**Contract**: Replace the default file. Register `Attraction` with a `ModelAdmin` that sets `list_display = ('name', 'category')` and `list_filter = ('category',)`.

### Success Criteria

#### Automated Verification

- `uv run python manage.py migrate` exits 0
- `uv run python manage.py check` exits 0
- `uv run python manage.py test` exits 0 (empty test suite at this point)

#### Manual Verification

- `uv run python manage.py shell -c "from attractions.models import Attraction; print(Attraction.objects.count())"` returns `0`
- `/admin/attractions/attraction/add/` loads and allows creating an attraction manually
- Category select in admin shows exactly four options

**Implementation Note**: Pause here for manual confirmation before Phase 3.

---

## Phase 3: Browse View + Filter + URL Routing + Templates

### Overview

Build everything the user interacts with: the `AttractionFilter`, the `attraction_list` view with HTMX branching and load-more logic, URL routing wired to the root `/`, and the three templates (full page, filter-results partial for category change, cards-append partial for load-more).

### Changes Required

#### 1. FilterSet

**File**: `attractions/filters.py` (new file)

**Intent**: Provide category filtering via a `FilterSet` backed by `ChoiceFilter`, including an "All categories" default option that returns the full queryset.

**Contract**: New file. `AttractionFilter(django_filters.FilterSet)` with:
- `category = django_filters.ChoiceFilter(choices=CATEGORY_CHOICES, empty_label='All categories')` — import `CATEGORY_CHOICES` from `attractions.models`
- `class Meta: model = Attraction; fields = ['category']`

#### 2. View

**File**: `attractions/views.py`

**Intent**: Handle three request modes from a single URL: (a) full-page load, (b) HTMX category filter change (returns `filter_results` partial), (c) HTMX load-more (returns `cards_append` partial with OOB button update).

**Contract**: Replace default file. The view reads `offset = int(request.GET.get('offset', 0))`, slices `f.qs[offset:offset + PAGE_SIZE]`, and determines `has_more = (offset + PAGE_SIZE) < f.qs.count()`. Dispatch logic:

```python
PAGE_SIZE = 6

def attraction_list(request):
    f = AttractionFilter(request.GET, queryset=Attraction.objects.all())
    offset = int(request.GET.get('offset', 0))
    qs = f.qs
    context = {
        'filter': f,
        'attractions': qs[offset:offset + PAGE_SIZE],
        'has_more': (offset + PAGE_SIZE) < qs.count(),
        'next_offset': offset + PAGE_SIZE,
    }
    if request.htmx:
        template = (
            'attractions/partials/cards_append.html' if offset > 0
            else 'attractions/partials/filter_results.html'
        )
        return render(request, template, context)
    return render(request, 'attractions/list.html', context)
```

#### 3. App URL config

**File**: `attractions/urls.py` (new file)

**Intent**: Define the single URL pattern for the attractions list inside the app's own URL config, keeping feature routing decoupled from project config (per AGENTS.md).

**Contract**: New file. `urlpatterns = [path('', views.attraction_list, name='attraction-list')]`.

#### 4. Root URL include

**File**: `corobimy/urls.py`

**Intent**: Wire the attractions app's URLs at the site root so `/` resolves to `attraction_list`. Add `include` to the existing import.

**Contract**: Add `from django.urls import path, include` (update existing import). Append `path('', include('attractions.urls'))` to `urlpatterns`. Place after the `health/` pattern so the health check is not shadowed.

#### 5. Full-page list template

**File**: `attractions/templates/attractions/list.html`

**Intent**: The full HTML page that users receive on direct navigation to `/`. Extends `base.html`, renders the filter form and the initial results section.

**Contract**: New file. Extends `base.html`. Contains:
- `<h1>Discover Kraków</h1>` (or equivalent heading)
- A `<form>` with `hx-get="{% url 'attraction-list' %}"`, `hx-target="#filter-results"`, `hx-trigger="change"`, `hx-swap="innerHTML"`, and `method="get"` — the `method` attribute preserves no-JS fallback; `hx-trigger="change"` fires on `<select>` change
- `{{ filter.form }}` (or `{{ filter.form.as_p }}`) inside the form — renders the category select
- A visually hidden submit button (`class="sr-only"`) for no-JS fallback
- `<div id="filter-results">{% include "attractions/partials/filter_results.html" %}</div>`

#### 6. Filter-results partial

**File**: `attractions/templates/attractions/partials/filter_results.html`

**Intent**: The full replaceable results section — contains the card grid and the load-more button container. Returned on category filter changes (HTMX `innerHTML` swap of `#filter-results`).

**Contract**: New file. Structure must be exactly:

```html
<div id="attraction-grid" class="grid ...">
  {% for attraction in attractions %}
    ...card...
  {% empty %}
    <p>No attractions found for this category.</p>
  {% endfor %}
</div>

<div id="load-more-container">
  {% if has_more %}
    <button hx-get="{% url 'attraction-list' %}?offset={{ next_offset }}{% if request.GET.category %}&category={{ request.GET.category }}{% endif %}"
            hx-target="#attraction-grid"
            hx-swap="beforeend">
      Load more
    </button>
  {% endif %}
</div>
```

`#load-more-container` must be a **sibling** of `#attraction-grid`, not nested inside it. See Critical Implementation Details.

#### 7. Cards-append partial

**File**: `attractions/templates/attractions/partials/cards_append.html`

**Intent**: Returns only the new card HTML to be appended to `#attraction-grid`, plus an OOB replacement of `#load-more-container` with the updated button (or empty div when all items are loaded).

**Contract**: New file. Two sections:
1. The new card HTML (same markup as one card in `filter_results.html`) — no wrapping div
2. `<div id="load-more-container" hx-swap-oob="true">` containing the load-more button (if `has_more`) or nothing (if all loaded)

The `hx-swap-oob="true"` attribute on `#load-more-container` tells HTMX to swap it independently from the main `beforeend` swap.

### Success Criteria

#### Automated Verification

- `uv run python manage.py check` exits 0
- `uv run python manage.py test attractions` exits 0 (even with an empty or minimal test suite at this stage)

#### Manual Verification

- `GET /` returns HTTP 200 with full HTML (confirm with `curl -s http://localhost:8000/ | head -20`)
- Filter form shows four category options plus "All categories"
- Selecting a category instantly replaces the card grid with no visible page reload (check Network tab — one XHR/fetch request, `HX-Request: true` header)
- With at least 7 attractions created in admin: "Load more" button appears, clicking it appends cards without replacing existing ones
- With fewer than 7 attractions of a category: no "Load more" button shown when that category is filtered
- With no attractions (empty DB): empty state message appears instead of cards
- Direct `?category=family` URL works (no-JS path)

**Implementation Note**: Pause here for manual confirmation before Phase 4. Test the HTMX interactions in the browser — open DevTools Network tab and confirm that category changes trigger XHR requests (not page reloads) and that the load-more button appends rather than replaces.

---

## Phase 4: Seed Data

### Overview

Populate `attractions/fixtures/initial_attractions.json` with 12 real Kraków attractions (3 per category), written for a local discovery audience with brief, honest descriptions. After `loaddata`, the feed is non-empty for demos and QA.

### Changes Required

#### 1. Fixture file

**File**: `attractions/fixtures/initial_attractions.json`

**Intent**: Provide a static, reproducible seed corpus of 12 Kraków attractions covering all four category filters. Descriptions are discovery-oriented, written for visitors who may already know the name but want a reason to go.

**Contract**: New file. 12 entries, `"model": "attractions.attraction"`. Primary keys 1–12. `created_at` set to `"2026-06-01T00:00:00Z"` for all entries (auto_now_add is bypassed by `loaddata`). Categories must use the slug values (`family`, `couples`, `sport`, `culture`), not display labels.

Full fixture content:

```json
[
  {
    "model": "attractions.attraction",
    "pk": 1,
    "fields": {
      "name": "Błonia Park",
      "category": "sport",
      "description": "48-hectare open meadow at the edge of the city used by locals for runs, cycling, and kite flying. Free, crowd-free on weekdays, and one of the few green spaces in Kraków that doesn't feel like a park.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 2,
    "fields": {
      "name": "Czartoryski Museum",
      "category": "culture",
      "description": "Poland's oldest public museum, home to Leonardo da Vinci's Lady with an Ermine. The building is 14th-century; the collection ranges from ancient Egyptian artefacts to Renaissance paintings.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 3,
    "fields": {
      "name": "Kazimierz District",
      "category": "couples",
      "description": "Kraków's former Jewish quarter, now full of independent cafes, jazz clubs, and second-hand bookshops. Best explored slowly in the evening when the lanterns come on.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 4,
    "fields": {
      "name": "Kraków Zoo",
      "category": "family",
      "description": "Walk-through enclosures set inside Las Wolski forest. Elephants, giraffes, and a petting paddock for young children. The forest setting makes it feel less like a zoo and more like a nature walk.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 5,
    "fields": {
      "name": "Oskar Schindler's Factory",
      "category": "culture",
      "description": "Award-winning museum documenting Kraków under Nazi occupation, set inside the actual enamel factory. Unsettling and essential — budget at least two hours.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 6,
    "fields": {
      "name": "Polish Aviation Museum",
      "category": "family",
      "description": "Over 200 aircraft in an open-air display: MiG jets, WWII bombers, and Cold War-era fighters. The outdoor collection is free to walk around; the main hall requires a ticket.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 7,
    "fields": {
      "name": "Rynek Główny",
      "category": "couples",
      "description": "One of Europe's largest medieval market squares. Beautiful at any hour, best at dusk when the Cloth Hall is lit and the crowds thin. Street musicians most evenings in summer.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 8,
    "fields": {
      "name": "Vistula Cycling Route",
      "category": "sport",
      "description": "Flat riverside path from Wawel Hill to Tyniec Abbey and back — about 30 km round trip. Bike rentals available near the riverbank. Views of the city from the opposite bank are the highlight.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 9,
    "fields": {
      "name": "Wawel Dragon Den",
      "category": "family",
      "description": "The legendary dragon's lair under Wawel Hill. Short cave walk with a fire-breathing steel dragon at the exit. Children under ten will tell the story for years.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 10,
    "fields": {
      "name": "Wawel Royal Castle Gardens",
      "category": "couples",
      "description": "Hillside gardens surrounding Wawel Castle with sweeping views over the Vistula. Quiet on weekday mornings and genuinely romantic at golden hour. Free to enter.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 11,
    "fields": {
      "name": "Wieliczka Salt Mine",
      "category": "culture",
      "description": "UNESCO World Heritage site 135 metres underground: hand-carved salt chapels, brine lakes, and chandeliers made of salt crystals. Book ahead — it sells out most weekends.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  },
  {
    "model": "attractions.attraction",
    "pk": 12,
    "fields": {
      "name": "Zakrzówek Reservoir",
      "category": "sport",
      "description": "Former limestone quarry now a turquoise swimming lake popular with local divers and cliff jumpers in summer. Ice skating when it freezes in winter. Not a tourist spot — entirely local.",
      "created_at": "2026-06-01T00:00:00Z"
    }
  }
]
```

#### 2. Load the fixture

**File**: shell command only

**Intent**: Populate the database with the seed corpus so the feed is non-empty for local development and post-deploy smoke testing.

**Contract**: Run `uv run python manage.py loaddata initial_attractions`. On Railway, run via `railway run uv run python manage.py loaddata initial_attractions` (requires a public Postgres URL or Railway SSH — see AGENTS.md).

### Success Criteria

#### Automated Verification

- `uv run python manage.py loaddata initial_attractions` exits 0 with output `Installed 12 object(s) from 1 fixture(s)`
- `uv run python manage.py shell -c "from attractions.models import Attraction; print(Attraction.objects.count())"` prints `12`
- `uv run python manage.py shell -c "from attractions.models import Attraction; cats = set(Attraction.objects.values_list('category', flat=True)); print(sorted(cats))"` prints `['couples', 'culture', 'family', 'sport']`

#### Manual Verification

- `GET /` shows 6 attraction cards (first page alphabetically: Błonia Park, Czartoryski Museum, Kazimierz District, Kraków Zoo, Oskar Schindler's Factory, Polish Aviation Museum)
- "Load more" button is visible below the six cards
- Clicking "Load more" appends the remaining 6 cards (Rynek Główny through Zakrzówek Reservoir)
- After load-more, the button disappears
- Filtering by `Families` shows exactly: Kraków Zoo, Polish Aviation Museum, Wawel Dragon Den — no load-more button
- Filtering by `Sport` shows exactly: Błonia Park, Vistula Cycling Route, Zakrzówek Reservoir — no load-more button
- Same pattern for `Couples` (Kazimierz District, Rynek Główny, Wawel Royal Castle Gardens) and `Culture` (Czartoryski Museum, Oskar Schindler's Factory, Wieliczka Salt Mine)

**Implementation Note**: Pause here for manual confirmation before Phase 5.

---

## Phase 5: Tests

### Overview

Write Django tests for the model, view (all three response modes), and FilterSet. After this phase `uv run python manage.py test` passes, and the test suite provides a regression baseline for S-02.

### Changes Required

#### 1. Test file

**File**: `attractions/tests.py`

**Intent**: Cover the model (fields, ordering, `__str__`), the view's three response modes (full page, HTMX filter change, HTMX load-more), category filtering, and the FilterSet queryset behaviour.

**Contract**: Replace the default empty file. Classes and cases to include:

**`AttractionModelTest`**
- `test_str_returns_name`: `str(attraction) == attraction.name`
- `test_default_ordering_is_alphabetical`: create attractions in reverse alpha order, assert `Attraction.objects.first().name` is the alphabetically first

**`AttractionListViewTest`** — `setUpTestData` creates 8 attractions (5 `culture`, 1 each of `family`, `couples`, `sport`) to trigger the load-more path on the unfiltered view:
- `test_full_page_returns_200`: `GET /`, status 200, uses template `attractions/list.html`
- `test_full_page_has_filter_form`: response HTML contains `<select` and `name="category"`
- `test_htmx_category_change_uses_partial`: `GET /?category=culture` with `HTTP_HX_REQUEST='true'`, uses template `attractions/partials/filter_results.html`
- `test_htmx_category_change_returns_only_matching`: response contains only culture attractions
- `test_htmx_load_more_uses_cards_append`: `GET /?offset=6` with `HTTP_HX_REQUEST='true'`, uses template `attractions/partials/cards_append.html`
- `test_htmx_load_more_appends_correct_slice`: context `attractions` queryset starts at offset 6
- `test_no_load_more_when_filtered`: `GET /?category=family` returns `has_more=False` when only 1 family attraction exists
- `test_empty_state_when_no_matches`: `GET /?category=sport` with only one sport attraction — verify `filter.qs.count() == 1` (not 0; edge case is category with zero results)

**`AttractionFilterTest`**
- `test_no_filter_returns_all`: `AttractionFilter({}, queryset=Attraction.objects.all()).qs.count()` equals total
- `test_category_filter_returns_correct_queryset`: filter by `culture`, verify only culture attractions returned
- `test_empty_label_allows_unfiltered`: passing `{'category': ''}` returns all attractions (empty_label choice maps to no-filter)

HTMX header in test client: pass `HTTP_HX_REQUEST='true'` as a kwarg to `self.client.get(...)`.

### Success Criteria

#### Automated Verification

- `uv run python manage.py test attractions` exits 0, all test cases pass
- No Django warnings in test output

#### Manual Verification

- Review test output for any skipped or errored tests
- Confirm the load-more path (offset > 0) uses `cards_append.html` and not `filter_results.html`

---

## Testing Strategy

### Unit Tests

- `Attraction` model: ordering, `__str__`, CATEGORY_CHOICES values
- `AttractionFilter`: queryset accuracy per category, empty-label unfiltered behaviour

### Integration Tests

- View returns correct template for each of the three request modes
- Category filter param correctly filters the queryset
- `has_more` flag correctly reflects remaining items
- Load-more offset slices the queryset correctly

### Manual Testing Steps

1. Start dev server: `uv run python manage.py runserver`
2. Open `http://localhost:8000/` — verify heading, 6 cards, load-more button visible
3. Open DevTools → Network tab. Select "Families" from the category filter — confirm one XHR request, no full page reload, grid updates instantly
4. Click "Load more" — confirm cards appended (DOM shows 12 total), button disappears
5. Select a category again after load-more — confirm grid resets to the 3 matching attractions, no stale cards from previous state
6. Select "Couples" — confirm exactly 3 cards, no load-more button
7. Disable JavaScript in DevTools — submit the filter form, confirm page reloads with correct filtered results (no-JS fallback)
8. Verify `/admin/attractions/attraction/` shows all 12 entries with name + category columns

## Migration Notes

The `Attraction` model migration is the first custom migration in the project. It runs as part of the Railway startup command (`railway.toml`). The migration is trivial (CREATE TABLE only) and will complete well within the 30-second Railway health check timeout.

Do not use `RunPython` in this migration. Seed data is loaded separately via `loaddata` after migration completes.

## References

- Research: `context/changes/attraction-browse-feed/research.md`
- Roadmap S-01: `context/foundation/roadmap.md:76-87`
- AGENTS.md hard rules: repo root, `startapp`, AppConfig
- F-01 Railway deploy context: `context/changes/railway-deploy-skeleton/`
- django-htmx HTMX OOB swap docs: https://django-htmx.readthedocs.io/

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Dependencies + Settings + Base Template

#### Automated

- [x] 1.1 `uv run python manage.py check` exits 0 — ea5a189
- [x] 1.2 `uv run python manage.py collectstatic --no-input` exits 0 — ea5a189

#### Manual

- [x] 1.3 Dev server starts with no import errors — ea5a189
- [x] 1.4 `/health/` still returns `{"status": "ok"}` — ea5a189

### Phase 2: Attraction App + Data Model

#### Automated

- [x] 2.1 `uv run python manage.py migrate` exits 0 — 22bbae8
- [x] 2.2 `uv run python manage.py check` exits 0 — 22bbae8
- [x] 2.3 `uv run python manage.py test` exits 0 — 22bbae8

#### Manual

- [x] 2.4 Shell query `Attraction.objects.count()` returns `0` — 22bbae8
- [x] 2.5 `/admin/attractions/attraction/add/` loads and shows exactly four category options — 22bbae8

### Phase 3: Browse View + Filter + URL Routing + Templates

#### Automated

- [x] 3.1 `uv run python manage.py check` exits 0 — ff47a2d
- [x] 3.2 `uv run python manage.py test attractions` exits 0 — ff47a2d

#### Manual

- [x] 3.3 `GET /` returns HTTP 200 with full HTML — ff47a2d
- [x] 3.4 Category filter triggers HTMX XHR (not page reload), grid updates instantly — ff47a2d
- [x] 3.5 Load-more appends cards without replacing existing ones (test with 7+ attractions in admin) — ff47a2d
- [x] 3.6 No-JS fallback: `?category=family` URL produces correct filtered results — ff47a2d
- [x] 3.7 Empty state message appears when DB is empty — ff47a2d

### Phase 4: Seed Data

#### Automated

- [x] 4.1 `uv run python manage.py loaddata initial_attractions` exits 0 with `Installed 12 object(s)` — 2db36ae
- [x] 4.2 Shell query `Attraction.objects.count()` returns `12` — 2db36ae
- [x] 4.3 All four category slugs present in DB — 2db36ae

#### Manual

- [x] 4.4 `GET /` shows 6 cards (Błonia Park … Polish Aviation Museum), load-more button visible — 2db36ae
- [x] 4.5 Load-more appends remaining 6 cards, button disappears — 2db36ae
- [x] 4.6 Each category filter shows exactly 3 cards with no load-more button — 2db36ae

### Phase 5: Tests

#### Automated

- [x] 5.1 `uv run python manage.py test attractions` exits 0, all tests pass
- [x] 5.2 No Django warnings in test output

#### Manual

- [x] 5.3 Review test output — no skipped or errored tests
- [x] 5.4 Load-more path confirmed using `cards_append.html` template

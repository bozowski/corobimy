---
change_id: attraction-browse-feed
type: combined-research
date: 2026-06-01T00:00:00+00:00
researcher: Claude (Sonnet 4.6)
git_commit: 0b5de4b3413a7b895c246ef097009a33d98543a0
branch: main
repository: corobimy
topic: "S-01 library compatibility + codebase baseline for attraction browse feed"
tags: research, codebase, attractions, django-filter, django-htmx, htmx, tailwind
status: complete
last_updated: 2026-06-01
last_updated_by: Claude (Sonnet 4.6)
sources: exa web search, context7, internal codebase sub-agents
---

# Research: S-01 Library Compatibility + Codebase Baseline

**Date**: 2026-06-01
**Researcher**: Claude (Sonnet 4.6)
**Git Commit**: 0b5de4b3413a7b895c246ef097009a33d98543a0
**Branch**: main
**Repository**: corobimy

## Research Question

Are the libraries identified in external research (django-filter, django-htmx, HTMX CDN, Tailwind CDN) compatible with the corobimy codebase? What does the baseline look like before implementing S-01?

---

## Summary

**All four libraries are compatible. No conflicts.** Two pip packages need adding (`django-filter`, `django-htmx`). The codebase is a clean Django 6.0.5 skeleton with zero feature apps — the attractions app, its models, templates, and URL wiring all need to be created from scratch. Three gotchas from F-01 carry forward into S-01: migrations are coupled to the startup command, there is no root (`/`) URL, and no base template exists.

---

## Internal Research: Codebase Compatibility

### Stack confirmed

| Item | Value | Source |
|------|-------|--------|
| Python | `>=3.13` | `pyproject.toml:4` |
| Django | `>=6.0.5` | `pyproject.toml:6` |
| gunicorn | `>=23.0.0` | `pyproject.toml:7` |
| psycopg[binary] | `>=3.2.0` | `pyproject.toml:8` |
| dj-database-url | `>=2.3.0` | `pyproject.toml:9` |
| whitenoise | `>=6.9.0` | `pyproject.toml:10` |
| django-filter | **not installed** | pyproject.toml |
| django-htmx | **not installed** | pyproject.toml |

No `requirements.txt` exists. Package manager: **uv** (`uv.lock` present).

---

### Library compatibility verdicts

#### django-filter 25.2 — COMPATIBLE

- Minimum Django required: 4.2. Installed: 6.0.5. ✓
- Minimum Python required: 3.8. Installed: 3.13. ✓
- Not yet in `pyproject.toml` — needs `uv add django-filter`.
- Needs `'django_filters'` added to `INSTALLED_APPS` (`settings.py:43`).
- No middleware required — pure app + template tag.
- No conflicts with current INSTALLED_APPS or MIDDLEWARE.

#### django-htmx — COMPATIBLE

- Minimum Django required: 4.2. Installed: 6.0.5. ✓
- Minimum Python required: 3.8. Installed: 3.13. ✓
- Not yet in `pyproject.toml` — needs `uv add django-htmx`.
- Needs `'django_htmx'` added to `INSTALLED_APPS` (`settings.py:43`).
- Needs `'django_htmx.middleware.HtmxMiddleware'` added to `MIDDLEWARE`.
  - Placement: after `WhiteNoiseMiddleware` (line 47), before `SessionMiddleware` (line 48) — or after it; either works.
- CSRF already configured (`CsrfViewMiddleware` at `settings.py:50`) → HTMX POST headers work out of the box.
- No conflicts.

#### HTMX (CDN) — COMPATIBLE

- No pip install. Loaded via `{% htmx_script %}` template tag (provided by django-htmx) or a manual `<script>` tag.
- Requires: Django template backend. Installed: `DjangoTemplates` (`settings.py:60`). ✓
- Requires: a base template. **Does not exist yet** — must be created.
- No conflicts.

#### Tailwind CSS (CDN Play) — COMPATIBLE

- No pip install, no Node/PostCSS build pipeline.
- Loaded as a `<link>` tag in the base template.
- WhiteNoise is configured for static assets (`settings.py:121-127`) but CDN Tailwind requires nothing from it. ✓
- No conflicts.

---

### Codebase baseline (what S-01 starts from)

#### Settings (`corobimy/settings.py`)

```
INSTALLED_APPS (lines 36-43): Django built-ins only
  - django.contrib.admin
  - django.contrib.auth
  - django.contrib.contenttypes
  - django.contrib.sessions
  - django.contrib.messages
  - django.contrib.staticfiles

MIDDLEWARE (lines 45-54):
  - SecurityMiddleware            ← line 46
  - WhiteNoiseMiddleware          ← line 47  (HtmxMiddleware goes here or after)
  - SessionMiddleware             ← line 48
  - CommonMiddleware              ← line 49
  - CsrfViewMiddleware            ← line 50  (CSRF already wired — HTMX POST works)
  - AuthenticationMiddleware      ← line 51
  - MessagesMiddleware            ← line 52
  - XFrameOptionsMiddleware       ← line 53

TEMPLATES (lines 58-71):
  - BACKEND: DjangoTemplates ✓
  - DIRS: []  ← no project-root templates dir yet
  - APP_DIRS: True  ← discovers templates/  inside each installed app ✓
  - context_processors: request, auth, messages ✓

STATIC (lines 121-127):
  - STATIC_URL: 'static/'
  - STATIC_ROOT: BASE_DIR / 'staticfiles'
  - STORAGES: CompressedManifestStaticFilesStorage (WhiteNoise) ✓
  - No STATIC_FILES_DIRS defined; no local static files exist yet

DATABASE (lines 79-84):
  - dj_database_url.config() reads DATABASE_URL env var
  - conn_max_age=60  ← CONN_MAX_AGE set (infrastructure requirement)
  - Local fallback: SQLite

LOGGING (lines 129-145):
  - django logger: WARNING+ → stdout ✓
  - SQL debug suppressed ✓

SECRET_KEY (lines 25-27):
  - Read from SECRET_KEY env var; raises ImproperlyConfigured if missing ✓
```

#### App structure

```
corobimy/                          ← project config package
  urls.py        — /admin/ + /health/ only; no root / wired
  views.py       — health() check only (JsonResponse)
  tests.py       — health check test only

No attractions/ app exists yet.
No templates/ directory anywhere.
No static/ directory (aside from staticfiles/ after collectstatic).
```

#### Deployment context (`railway.toml`)

Start command (from F-01):
```
python manage.py collectstatic --no-input && python manage.py migrate && gunicorn corobimy.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --access-logfile -
```

- **Migrations are coupled to the gunicorn start command.** S-01's first `Attraction` model migration runs on deploy. Keep it fast (no data transforms, no large existing tables).
- Railway health check: pings `/health/` every 30 s; 30 s timeout. Migration + collectstatic must complete within this window.
- Production URL: `https://web-production-1188c.up.railway.app`

---

### Integration checklist for plan phase

The following changes are needed to make all four libraries work — **this is a summary for `/10x-plan`, not an implementation sequence**:

1. `uv add django-filter django-htmx` → updates `pyproject.toml` and `uv.lock`
2. `INSTALLED_APPS`: append `'django_filters'`, `'django_htmx'`, `'attractions'` (`settings.py:43+`)
3. `MIDDLEWARE`: insert `'django_htmx.middleware.HtmxMiddleware'` after `WhiteNoiseMiddleware` (line 47)
4. Create `attractions/` Django app (sibling to `manage.py`)
   - `attractions/models.py` — `Attraction` model with `name`, `category`, `description` fields
   - `attractions/filters.py` — `AttractionFilter(FilterSet)` with `ChoiceFilter` on `category`
   - `attractions/views.py` — `attraction_list` view branching on `request.htmx`
   - `attractions/urls.py` — route to attraction list view
   - `attractions/fixtures/initial_attractions.json` — seed data (Kraków corpus)
5. Create templates:
   - `attractions/templates/base.html` (or project-level `corobimy/templates/base.html`) — loads Tailwind CDN + `{% htmx_script %}`
   - `attractions/templates/attractions/list.html` — full page (extends base)
   - `attractions/templates/attractions/partials/grid.html` — card grid (returned by HTMX request)
6. Wire in `corobimy/urls.py`: `path('', include('attractions.urls'))` (or `path('attractions/', ...)`)
7. Decide: root `/` = attractions list directly, or redirect

---

### Gotchas and constraints carried from F-01

| Gotcha | Impact on S-01 | How to handle |
|--------|---------------|---------------|
| Migrations coupled to startup | First `Attraction` migration runs on deploy; health check has 30 s timeout | Keep initial migration minimal (no data in migration itself); use `loaddata` for seed data separately |
| No root path (`/`) wired | S-01 is the first user-facing page; needs a URL decision | Wire attractions list at `''` (root) in `corobimy/urls.py` — cleanest for MVP |
| No base template exists | HTMX and Tailwind need a base template to load from | Create `attractions/templates/base.html` or add `DIRS` and a project-level `templates/` |
| No `STATIC_FILES_DIRS` | CDN approach avoids needing local CSS; no action for MVP | Use CDN only; defer local static files to post-MVP |
| SECRET_KEY hardened | Must be set in Railway Variables | Already set from F-01 |

---

## External Research: S-01 Library Candidates

> Libraries compatible with Django 6.0.5 + PostgreSQL + uv for the attraction browse feed (anonymous filtering by category).
> Source: exa web search, 2026-06-01.

## Category filtering

| Library | Version | Verdict |
|---------|---------|---------|
| **`django-filter`** | 25.2 | **Use.** `FilterSet` + `ChoiceFilter` handles fixed-choice categories (family/couples/sport/culture). Ships `FilterView` CBV that wires into templates. Actively maintained. |
| Built-in `get_queryset()` override | — | Works for a single `?category=` param but django-filter gives form validation and template integration for free. |

**Usage sketch:**
```python
class AttractionFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(choices=CATEGORY_CHOICES)

    class Meta:
        model = Attraction
        fields = ['category']
```

Docs: https://django-filter.readthedocs.io/en/latest/

---

## Frontend interactivity (filter without full page reload)

| Library | How installed | Verdict |
|---------|--------------|---------|
| **HTMX** | CDN (~14 KB) | **Use.** `hx-get` on the filter form swaps the card grid partial — no JS written. Strong Django ecosystem fit in 2025/2026. |
| **`django-htmx`** | `pip install django-htmx` | **Use alongside HTMX.** Adds `HtmxMiddleware` and `request.htmx` flag so views branch on partial vs full-page request. |
| Alpine.js | CDN (~15 KB) | Optional. Useful for pure client-side UI state (active filter chip highlight, toggle states). Not needed for the filter fetch itself. |
| `django-nitro` | pip | Ships batteries-included `NitroListView` with filters + pagination via HTMX. Interesting but targets Django 5.2+ — compatibility with 6.0.5 unverified. Skip for now. |

**HTMX pattern for category filter:**
```html
<!-- filter form triggers partial swap -->
<form hx-get="/attractions/" hx-target="#attraction-grid" hx-trigger="change">
  <select name="category">...</select>
</form>

<div id="attraction-grid">
  {% include "attractions/partials/grid.html" %}
</div>
```

```python
# view branches on request.htmx
def attraction_list(request):
    f = AttractionFilter(request.GET, queryset=Attraction.objects.all())
    if request.htmx:
        return render(request, "attractions/partials/grid.html", {"filter": f})
    return render(request, "attractions/list.html", {"filter": f})
```

Evidence: recipe_site (Django 5 + HTMX + Alpine.js + Tailwind + PostgreSQL + WhiteNoise — same stack profile); htmx-django-starter (Django 5, HTMX patterns documented); Medium benchmark article (HTMX won on simplicity and server integration vs Alpine.js for server-driven UIs).

---

## CSS / UI

| Option | Verdict |
|--------|---------|
| **Tailwind CSS** (CDN Play) | **Use.** Utility classes, no build step for MVP. Consistent pairing across all HTMX + Django repos found. |
| Bootstrap 5 (CDN) | Safe fallback — card components built in, more opinionated styling. |

Tailwind CDN is sufficient for MVP; no PostCSS/Node pipeline needed.

---

## Seed data (Kraków attraction corpus)

| Approach | Verdict |
|----------|---------|
| **JSON fixture + `loaddata`** | **Use for static MVP seed.** Store in `attractions/fixtures/initial_attractions.json`, run once post-migrate. No extra library. |
| Custom management command (`get_or_create`) | Better when seed data needs environment branching or idempotency. Preferred if corpus grows or needs conditional logic. |
| Data migration (`RunPython` + `loaddata`) | **Avoid.** Documented pitfall: uses current model version against historical schema; breaks on future field additions. |

**Fixture format (JSON):**
```json
[
  {
    "model": "attractions.attraction",
    "pk": 1,
    "fields": {
      "name": "Wawel Castle",
      "category": "culture",
      "description": "..."
    }
  }
]
```

Load: `python manage.py loaddata initial_attractions`

---

## Recommended pip installs

```
django-filter
django-htmx
```

HTMX and Tailwind CSS loaded via CDN in base template (no build step).

---

## What this research does NOT answer

- Which Tailwind version / CDN URL to pin (verify latest stable at plan time).
- `django-nitro` Django 6.0.5 compatibility — needs a quick check before adopting.
- Seed data content: actual Kraków attraction names, descriptions, category assignments — this is editorial work, not a library decision.
- Pagination library choice (Django's built-in `Paginator` vs HTMX infinite scroll) — deferred to plan.
- Root URL decision: `/` vs `/attractions/` — deferred to plan.

---

## Library Documentation (fetched via Context7 / WebFetch)

### django-filter

**FilterSet + ChoiceFilter (fixed-choice categories)**

```python
CATEGORY_CHOICES = [
    ('family', 'Family'),
    ('couples', 'Couples'),
    ('sport', 'Sport'),
    ('culture', 'Culture'),
]

class AttractionFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(choices=CATEGORY_CHOICES)
    # empty_label defaults to FILTERS_EMPTY_CHOICE_LABEL (shows "All" option)

    class Meta:
        model = Attraction
        fields = ['category']
```

- `empty_label` — display label when no filter is selected (shows all results).
- `null_label` / `null_value` — only needed if the field can be NULL; not needed here.
- `TypedChoiceFilter` — extends ChoiceFilter with a `coerce` callable; not needed for string slugs.

**FilterView CBV**

```python
# urls.py
from django_filters.views import FilterView
from .models import Attraction
from .filters import AttractionFilter

urlpatterns = [
    path('', FilterView.as_view(
        model=Attraction,
        filterset_class=AttractionFilter,
        template_name='attractions/list.html',
    ), name='attraction-list'),
]
```

Default template name convention: `<app>/<model>_filter.html`.

**Template — form + queryset**

```django
<form method="get">
    {{ filter.form.as_p }}
    <input type="submit" value="Filter" />
</form>

{% for attraction in filter.qs %}
    {{ attraction.name }}
{% endfor %}
```

`filter.qs` is the filtered queryset — iterate it directly in templates.

---

### django-htmx

**Installation**

```
uv add django-htmx
```

`settings.py`:
```python
INSTALLED_APPS = [
    ...
    "django_htmx",
]

MIDDLEWARE = [
    ...
    "django_htmx.middleware.HtmxMiddleware",  # position: after SecurityMiddleware is fine
]
```

**Base template wiring**

```django
{% load django_htmx %}
<body hx-headers='{"x-csrftoken": "{{ csrf_token }}"}'>
    {% htmx_script %}
    ...
</body>
```

`{% htmx_script %}` injects the HTMX `<script>` tag. The `hx-headers` body attribute forwards the CSRF token on all HTMX POST requests.

**`request.htmx` attributes**

| Attribute | Type | Use |
|-----------|------|-----|
| `bool(request.htmx)` | bool | `True` if `HX-Request: true` header present — main branch condition |
| `request.htmx.target` | str\|None | ID of the target element |
| `request.htmx.trigger` | str\|None | ID of the element that triggered the request |
| `request.htmx.trigger_name` | str\|None | `name` attribute of the triggering element |
| `request.htmx.current_url` | str\|None | Full URL of the page that made the request |
| `request.htmx.boosted` | bool | True if request came from `hx-boost` |

**View pattern — partial vs full page**

```python
def attraction_list(request):
    f = AttractionFilter(request.GET, queryset=Attraction.objects.all())
    template = "attractions/partials/grid.html" if request.htmx else "attractions/list.html"
    return render(request, template, {"filter": f})
```

**Caching note:** if the view is cached, add `Vary: HX-Request` to avoid serving a partial to a full-page request:
```python
from django.views.decorators.vary import vary_on_headers

@vary_on_headers("HX-Request")
def attraction_list(request): ...
```

---

### HTMX (CDN)

Load via `{% htmx_script %}` (django-htmx handles the script tag) or manually:
```html
<script src="https://unpkg.com/htmx.org@2.x" defer></script>
```

**Key attributes for the category filter pattern**

| Attribute | Value | Effect |
|-----------|-------|--------|
| `hx-get` | `/` or named URL | Sends GET request on trigger |
| `hx-target` | `#attraction-grid` | CSS selector of element to update |
| `hx-trigger` | `change` (default for `<select>`) | Event that fires the request |
| `hx-swap` | `innerHTML` (default) | Replaces content inside target |

**Filter form pattern (select-based)**

```html
<form hx-get="{% url 'attraction-list' %}"
      hx-target="#attraction-grid"
      hx-trigger="change">
    {{ filter.form.as_p }}
</form>

<div id="attraction-grid">
    {% include "attractions/partials/grid.html" %}
</div>
```

- `hx-trigger="change"` fires when any `<select>` inside the form changes.
- No submit button needed for instant filtering; keep one for no-JS fallback.
- `delay` modifier: `hx-trigger="change delay:300ms"` debounces rapid changes.

**Partial template** (`attractions/partials/grid.html`):
```django
{% for attraction in filter.qs %}
<div class="card">
    <h2>{{ attraction.name }}</h2>
    <p>{{ attraction.category }}</p>
</div>
{% empty %}
<p>No attractions found for this filter.</p>
{% endfor %}
```

The server returns only this fragment on HTMX requests; HTMX swaps it into `#attraction-grid`.

---

## Code References

- `corobimy/settings.py:36-43` — INSTALLED_APPS (where django_filters, django_htmx, attractions go)
- `corobimy/settings.py:45-54` — MIDDLEWARE (where HtmxMiddleware slots in after line 47)
- `corobimy/settings.py:58-71` — TEMPLATES (DjangoTemplates, APP_DIRS=True confirmed)
- `corobimy/settings.py:79-84` — DATABASE (dj_database_url, conn_max_age=60)
- `corobimy/settings.py:121-127` — STATIC_FILES / WhiteNoise config
- `corobimy/urls.py:21-24` — current URL patterns (admin + health only)
- `corobimy/views.py` — health check view only; attractions view needs creating
- `pyproject.toml:4-10` — full dependency list; django-filter and django-htmx absent

## Architecture Insights

- The project is a clean Django 6.0.5 skeleton — no accidental complexity to work around.
- `APP_DIRS=True` means templates in `attractions/templates/` are auto-discovered without changing `settings.py:DIRS`.
- WhiteNoise is production-ready but has nothing to serve yet; CDN-only approach for MVP avoids the `collectstatic` concern for CSS.
- The HTMX + django-filter pattern from external research maps cleanly onto this stack: no template backend mismatch, no middleware conflicts, no static-asset pipeline required.
- Migrations on first deploy are safe as long as the `Attraction` model migration is trivial (no backfill, no ALTER on existing large table).

## Historical Context (from prior changes)

- `context/changes/railway-deploy-skeleton/` — F-01 implementation established the deployment pipeline, settings patterns, health check, and logging. All conventions carried forward into S-01.

## Open Questions

- **Root URL**: Should the attractions list live at `/` (root) or `/attractions/`? Most natural MVP choice is `/` — deferred to `/10x-plan`.
- **Base template location**: Project-level `corobimy/templates/base.html` (add path to `DIRS`) vs app-level `attractions/templates/base.html`. Project-level is better for future S-02 auth templates reusing the same base — deferred to `/10x-plan`.
- **Seed data content**: Actual Kraków attraction names, descriptions, category assignments — editorial work, not covered by library research.
- **Pagination**: Django built-in `Paginator` vs HTMX infinite scroll — deferred to plan.
- **Tailwind CDN URL**: Pin to a specific version at plan time (check latest stable).

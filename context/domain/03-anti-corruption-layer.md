---
title: "corobimy — Anti-Corruption Layer: django-filter"
created: 2026-06-28
type: refactor-plan
source: context/domain/01-domain-distillation.md
---

# Anti-Corruption Layer — plan refaktoru

## KROK 0 — Kontekst

### Manifest zależności (pyproject.toml)

| Pakiet | Wersja | Rola |
|---|---|---|
| `django` | ≥6.0.5 | Framework — standardowo obecny w całym projekcie |
| `django-filter` | ≥25.2 | Filtrowanie QuerySet przez HTTP params |
| `django-htmx` | ≥1.27.0 | Middleware + template tags dla HTMX |
| `sentry-sdk[django]` | ≥2.0 | Monitoring błędów |
| `dj-database-url` | ≥2.3.0 | Parsowanie DATABASE_URL |
| `whitenoise` | ≥6.9.0 | Serwowanie plików statycznych |
| `psycopg[binary]` | ≥3.2.0 | Driver PostgreSQL |
| `gunicorn` | ≥23.0.0 | WSGI server |

### Stack i warstwy kodu

| Warstwa | Pliki |
|---|---|
| Konfiguracja | `corobimy/settings.py` |
| Domain / Persystencja | `attractions/models.py` |
| Application | `attractions/views.py`, `accounts/views.py` |
| Query / Filter | `attractions/filters.py` |
| UI / Templates | `attractions/templates/**/*.html`, `templates/**/*.html` |
| Tests | `attractions/tests.py`, `accounts/tests.py` |

---

## KROK 1 — Identyfikacja przeciekających zależności

### Kandydat A: `django-filter` (`django_filters`)

**Wszystkie pliki znające tę zależność**:

| Plik:linia | Użycie |
|---|---|
| `pyproject.toml:12` | deklaracja zależności |
| `corobimy/settings.py:56` | `"django_filters"` w `INSTALLED_APPS` |
| `attractions/filters.py:1` | `import django_filters` |
| `attractions/filters.py:6` | `class AttractionFilter(django_filters.FilterSet):` |
| `attractions/filters.py:7-10` | `django_filters.ChoiceFilter(choices=..., empty_label=...)` |
| `attractions/views.py:5` | `from attractions.filters import AttractionFilter` |
| `attractions/views.py:12` | `f = AttractionFilter(request.GET, queryset=Attraction.objects.all())` |
| `attractions/views.py:17` | `qs = f.qs` — dostęp do własności FilterSet |
| `attractions/views.py:30` | `"filter": f` — surowy obiekt FilterSet trafia do kontekstu szablonu |
| `attractions/tests.py:5` | `from attractions.filters import AttractionFilter` |
| `attractions/tests.py:103` | `f = AttractionFilter({}, queryset=Attraction.objects.all())` |
| `attractions/tests.py:107` | `f = AttractionFilter({"category": "culture"}, ...)` |
| `attractions/tests.py:113` | `f = AttractionFilter({"category": ""}, ...)` |
| `attractions/templates/attractions/list.html:17` | `{{ filter.form.as_p }}` — dostęp do `FilterSet.form.as_p()` w szablonie |

**Dodatkowy sygnał — `context/foundation/lessons.md:5-13`**:

```
Rule: When building HTMX pagination URLs, serialise the full filter form data
(e.g. f.form.data) rather than listing individual params.
Applies to: Any template that renders a Load More or paginate button
alongside a django-filters filter form.
```

Lekcja explicite zaleca, żeby szablony używały `f.form.data` (API `django-filter`) do
budowania URL paginacji — to pogłębiłoby coupling szablonu z biblioteką, gdyby lekcja była
wdrożona. Aktualny kod tego NIE robi i ręcznie wątki `request.GET.category` w szablonach
(`filter_results.html:19`, `cards_append.html:15`) — co powoduje osobny bug (inne filtry
byłyby gubione przy Load More).

---

### Kandydat B: `django-htmx`

**Wszystkie pliki znające tę zależność**:

| Plik:linia | Użycie |
|---|---|
| `pyproject.toml:13` | deklaracja zależności |
| `corobimy/settings.py:57` | `"django_htmx"` w `INSTALLED_APPS` |
| `corobimy/settings.py:65` | `"django_htmx.middleware.HtmxMiddleware"` w `MIDDLEWARE` |
| `attractions/views.py:36` | `if request.htmx:` — branch na atrybut middleware |
| `attractions/views.py:58` | `if request.htmx:` — second branch |
| `templates/base.html:1` | `{% load django_htmx %}` |
| `templates/base.html:11` | `{% htmx_script %}` — renderuje tag `<script>` dla HTMX JS |

---

### Kandydat C: `sentry-sdk`

Wyłącznie `corobimy/settings.py:17,20-25` — izolowany w konfiguracji. Nie przecieka.

### Kandydat D: `dj-database-url`

Wyłącznie `corobimy/settings.py:16,98-101` — izolowany w konfiguracji. Nie przecieka.

### Kandydat E: `whitenoise`

Wyłącznie `corobimy/settings.py:64,143` — izolowany w konfiguracji. Nie przecieka.

---

## KROK 2 — Klasyfikacja i wybór #1

### Tabela ocen

| Kandydat | (a) Liczba warstw/plików | (b) Koszt wymiany dziś | (c) Deklarowana wymienialność | Wynik |
|---|---|---|---|---|
| **`django-filter`** | **5 plików, 14 miejsc, 4 warstwy**: config, query, application, UI, tests | Wysoki — zmiana `filters.py` wymusiłaby zmiany w `views.py`, `tests.py` i `list.html` (template dostaje FilterSet i woła `.form.as_p()`) | PRD FR-003 nazywa "preference filter" konceptem domenowym (prd.md:68), nigdzie nie ma wzmianki o `django-filter` jako wymaganiu | **NAJWYŻSZY** |
| `django-htmx` | 3 pliki, 7 miejsc, 3 warstwy: config, application, UI | Średni — `if request.htmx:` w 2 widokach, `{% htmx_script %}` w base.html | AGENTS.md:43 deklaruje "no frontend JS framework in MVP scope" — htmx jest świadomym wyborem | Wysoki |
| `sentry-sdk` | 1 plik, 1 warstwy: config | Niski — 5 linii w settings.py | brak | Niski |
| `dj-database-url` | 1 plik, 1 warstwa: config | Niski | brak | Niski |
| `whitenoise` | 1 plik, 1 warstwa: config | Niski | brak | Niski |

### Wybrany kandydat #1: `django-filter`

**Uzasadnienie**:

1. **Najgłębsze naruszenie granicy warstw**: obiekt `FilterSet` (`f`) jest przekazywany w
   kontekście widoku jako `"filter": f` (`views.py:30`) i trafia do szablonu UI (`list.html:17`),
   który woła `filter.form.as_p()` — API wewnętrzne biblioteki jest dostępne w warstwie
   prezentacyjnej. To jest podręcznikowy przykład "typy biblioteki w kontrakcie wire".

2. **Lekcja domenowa (lessons.md:13)** zaleca pogłębienie couplingу (`f.form.data` w
   szablonach) — to oznacza, że naturalny kierunek ewolucji projektu prowadzi DO WIĘKSZEGO
   uzależnienia, nie mniejszego. Bez ACL każdy nowy filtr będzie automatycznie przeciekał przez
   te same ścieżki.

3. **PRD deklaruje concept domenowy** (FR-003: "preference filter"), a kod wyraża go przez
   typ biblioteczny (`FilterSet`). Rozjazd intencja-vs-kod jest wyraźny.

4. **Testy warstwy domenowej importują adapter bezpośrednio**: `AttractionFilterTest`
   (`tests.py:95-114`) testuje `AttractionFilter` przez bezpośrednie instancjonowanie —
   warstwa testów jest sprzężona z biblioteką, nie z domeną.

---

## KROK 3 — Diagnoza

### Duplikacje i przecieki przez granice

#### Granica 1: Application → UI (najpoważniejsza)

Widok (`views.py:30`) przekazuje surowy obiekt `FilterSet` jako zmienną kontekstową:

```python
# attractions/views.py:29-35
context = {
    "filter": f,                     # ← FilterSet (django-filter) w kontrakcie wire
    "attractions": page_attractions,
    "has_more": (offset + PAGE_SIZE) < total,
    "next_offset": offset + PAGE_SIZE,
    "saved_pks": saved_pks,
}
```

Szablon (`list.html:17`) wołuje API biblioteki:

```html
{{ filter.form.as_p }}
```

`filter.form` to atrybut `FilterSet`; `.as_p()` to metoda `BaseForm` — dwa poziomy
bibliotecznego API obecne w warstwie UI. Wymiana `django-filter` wymaga zmiany szablonu.

#### Granica 2: Application layer — wiedza o FilterSet

`views.py:12` inicjalizuje FilterSet z `request.GET` (pakuje surowy `QueryDict` biblioteki):

```python
# attractions/views.py:12
f = AttractionFilter(request.GET, queryset=Attraction.objects.all())
```

`views.py:17` używa właściwości `.qs` — specyficznego API FilterSet:

```python
# attractions/views.py:17
qs = f.qs
```

Widok zna: konstruktor `FilterSet`, wzorzec `(data, queryset=)`, właściwość `.qs`. Wymiana
biblioteki wymaga zmiany widoku.

#### Granica 3: Tests → FilterSet bezpośrednio

`tests.py:5,103,107,113` importuje i instancjonuje `AttractionFilter` bezpośrednio, sprawdzając
`.qs.count()`:

```python
# attractions/tests.py:103-114
f = AttractionFilter({}, queryset=Attraction.objects.all())
self.assertEqual(f.qs.count(), 3)

f = AttractionFilter({"category": "culture"}, queryset=Attraction.objects.all())
self.assertEqual(f.qs.count(), 2)
```

Warstwa testów pomija domenę i sprawdza zachowanie biblioteki bezpośrednio. Jeśli
`django-filter` zmieni API (np. `.qs` → `.queryset`), testy się złamią — nie dlatego, że
domena się zmieniła, ale dlatego, że biblioteka się zmieniła.

#### Granica 4: URL paginacji — lekcja wdrożona połowicznie

`lessons.md:5-13` zdiagnozował problem: pagination URL ręcznie wątki `request.GET.category`
zamiast serializować pełen `f.form.data`. Aktualne szablony (`filter_results.html:19`,
`cards_append.html:15`) nadal używają ręcznego wątkowania:

```html
<!-- filter_results.html:19 -->
?offset={{ next_offset }}{% if request.GET.category %}&category={{ request.GET.category }}{% endif %}
```

Lekcja zaleca `f.form.data`, co oznacza że "poprawka" z lekcji POGŁĘBIA coupling szablonu z
biblioteką. ACL rozwiązuje ten dylemat inaczej: adapter serializuje dane filtra, szablon
dostaje gotowy string.

---

## KROK 4 — Projekt ACL

### Struktura docelowa

```
attractions/
├── domain.py      ← Value Object: ActivePreferenceFilter (istniejący/rozszerzony)
├── ports.py       ← NOWY: Port domenowy (Protocol)
├── adapters.py    ← NOWY: Adapter (jedyne miejsce znające django-filter + AttractionFilter)
├── filters.py     ← BEZ ZMIAN: FilterSet żyje tutaj, ale dostępny tylko przez adapter
└── views.py       ← importuje port, NIE importuje AttractionFilter
```

### 4.1 Value Object (domain layer)

```python
# attractions/domain.py  (nowy fragment — dołącz do istniejącego pliku)

from dataclasses import dataclass
from django.utils.safestring import SafeString


@dataclass(frozen=True)
class ActivePreferenceFilter:
    """
    Value object — stan aktywnego filtra preferencji użytkownika.
    Przenosi gotowe dane do szablonu; żaden szablon nie zna django-filter.

    Invariant: form_html jest SafeString (zaufany HTML z formularza Django).
    Invariant: pagination_params nie zawiera klucza 'offset'.
    """
    selected_category: str | None     # slug ('family', 'culture', …) lub None
    form_html: SafeString             # gotowy HTML pola <select>
    pagination_params: str            # URL-encoded, np. "category=family"
```

### 4.2 Port domenowy

```python
# attractions/ports.py  (NOWY PLIK)

from typing import Protocol
from django.db.models import QuerySet
from django.http import QueryDict

from attractions.domain import ActivePreferenceFilter


class IPreferenceFilterBuilder(Protocol):
    """
    Port domenowy — kontrakt między widokiem a implementacją filtra.
    Widok zna wyłącznie ten interfejs; nie zna django-filter.
    """

    def build(self, data: QueryDict) -> ActivePreferenceFilter:
        """
        Buduje ActivePreferenceFilter z danych HTTP GET.
        Nigdy nie rzuca — nieprawidłowa lub pusta wartość → selected_category=None.
        """
        ...

    def apply(self, data: QueryDict, queryset: QuerySet) -> QuerySet:
        """
        Stosuje filtr do QuerySet. Zwraca nowy (leniwy) QuerySet.
        Operacja wyłącznie read-only.
        """
        ...
```

### 4.3 Adapter — jedyne miejsce wiedzące o django-filter

```python
# attractions/adapters.py  (NOWY PLIK)

from django.http import QueryDict
from django.db.models import QuerySet
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from attractions.domain import ActivePreferenceFilter
from attractions.filters import AttractionFilter   # ← jedyny legalny import poza tym plikiem


class DjangoFilterPreferenceFilterAdapter:
    """
    Adapter implementujący IPreferenceFilterBuilder przez django-filter.
    Jest to JEDYNE miejsce w projekcie, które może importować AttractionFilter
    lub django_filters. Wymiana biblioteki = zmiana tylko tego pliku.
    """

    def build(self, data: QueryDict) -> ActivePreferenceFilter:
        """
        Preconditions: data to QueryDict (może być pusty).
        Sygnatury: ActivePreferenceFilter z:
          - selected_category: validowany slug lub None
          - form_html: wynik f.form.as_p() jako SafeString
          - pagination_params: URL-encoded kopia data bez 'offset'

        Nie rzuca na nieznaną kategorię — django-filter ignoruje nieznane wartości.
        """
        f = AttractionFilter(data, queryset=AttractionFilter.Meta.model.objects.none())
        category = data.get('category') or None

        params_without_offset = {k: v for k, v in data.items() if k != 'offset'}
        pagination_params = urlencode(params_without_offset)

        return ActivePreferenceFilter(
            selected_category=category,
            form_html=mark_safe(f.form.as_p()),
            pagination_params=pagination_params,
        )

    def apply(self, data: QueryDict, queryset: QuerySet) -> QuerySet:
        """
        Stosuje filtr do przekazanego QuerySet.
        Zwraca leniwy QuerySet — brak zapytania do DB tutaj.
        """
        return AttractionFilter(data, queryset=queryset).qs
```

> **Uwaga dotycząca `AttractionFilter.Meta.model`**: metoda `build` tworzy FilterSet z pustym
> QuerySet (tylko po to, żeby wyrenderować formularz — bez zapytania do DB). Alternatywnie
> można stworzyć instancję formularza bezpośrednio: `AttractionFilter(data).form.as_p()`, co
> wymaga sprawdzenia, czy FilterSet obsługuje brak `queryset`. Decyzję o szczegółowej
> inicjalizacji zapisz w adapterze, nie w widoku.

### 4.4 Widok po refaktorze

```python
# attractions/views.py  (szkic po refaktorze — fragment attraction_list)

# USUNIĘTE: from attractions.filters import AttractionFilter
from attractions.adapters import DjangoFilterPreferenceFilterAdapter
from attractions.domain import ActivePreferenceFilter

_filter_adapter = DjangoFilterPreferenceFilterAdapter()

def attraction_list(request):
    pref_filter: ActivePreferenceFilter = _filter_adapter.build(request.GET)
    qs = _filter_adapter.apply(request.GET, Attraction.objects.all())

    try:
        offset = max(0, int(request.GET.get("offset", 0)))
    except (ValueError, TypeError):
        offset = 0

    total = qs.count()
    page_attractions = list(qs[offset : offset + PAGE_SIZE])

    if request.user.is_authenticated:
        page_pks = [a.pk for a in page_attractions]
        saved_pks = set(
            UserSavedAttraction.objects.filter(
                user=request.user, attraction_id__in=page_pks
            ).values_list("attraction_id", flat=True)
        )
    else:
        saved_pks = set()

    context = {
        "pref_filter": pref_filter,    # domain VO, NIE FilterSet
        "attractions": page_attractions,
        "has_more": (offset + PAGE_SIZE) < total,
        "next_offset": offset + PAGE_SIZE,
        "saved_pks": saved_pks,
    }
    if request.htmx:
        template = (
            "attractions/partials/cards_append.html"
            if offset > 0
            else "attractions/partials/filter_results.html"
        )
        return render(request, template, context)
    return render(request, "attractions/list.html", context)
```

### 4.5 Rozstrzygnięcie otwartego pytania z lessons.md

**Problem z lessons.md**: paginacja powinna serializować pełen `f.form.data` — ale to
pogłębia coupling szablonu z biblioteką.

**Rozstrzygnięcie przez ACL**: adapter (`DjangoFilterPreferenceFilterAdapter.build`) buduje
`pagination_params: str` z pełnych danych filtra (bez `offset`) i dostarcza go w
`ActivePreferenceFilter`. Szablon dostaje gotowy string — nie wie nic o `f.form.data`.

**Zakodowanie decyzji**: w `adapters.py`, linia:

```python
params_without_offset = {k: v for k, v in data.items() if k != 'offset'}
pagination_params = urlencode(params_without_offset)
```

Jeśli w przyszłości `AttractionFilter` dostanie nowe pole (np. `city`), logika serializacji
jest w jednym miejscu — adapter. Szablony nie trzeba dotykać.

---

## KROK 5 — Dowód izolacji + Before/After

### Proof: wymiana django-filter dotyka TYLKO adaptera

| Co zmienia się przy wymianie biblioteki | Plik |
|---|---|
| Adapter importuje inną bibliotekę | `attractions/adapters.py` (jedyny plik) |
| `AttractionFilter` → inny FilterSet | `attractions/filters.py` |
| **NIE zmienia się** | `attractions/views.py` |
| **NIE zmienia się** | `attractions/tests.py` (testy widoku) |
| **NIE zmienia się** | `attractions/templates/**/*.html` |
| **NIE zmienia się** | `corobimy/settings.py` (django_filters w INSTALLED_APPS nadal potrzebny) |

### Before / After dla każdego miejsca reguły

#### `attractions/views.py:5`

```python
# BEFORE
from attractions.filters import AttractionFilter

# AFTER
from attractions.adapters import DjangoFilterPreferenceFilterAdapter
```

#### `attractions/views.py:12,17,30`

```python
# BEFORE
f = AttractionFilter(request.GET, queryset=Attraction.objects.all())
qs = f.qs
context = { "filter": f, ... }

# AFTER
pref_filter = _filter_adapter.build(request.GET)
qs = _filter_adapter.apply(request.GET, Attraction.objects.all())
context = { "pref_filter": pref_filter, ... }
```

#### `attractions/templates/attractions/list.html:17`

```html
<!-- BEFORE: szablon woła django-filter API -->
{{ filter.form.as_p }}

<!-- AFTER: szablon renderuje gotowy string domenowy -->
{{ pref_filter.form_html }}
```

#### `filter_results.html:19`, `cards_append.html:15`

```html
<!-- BEFORE: ręczne wątkowanie konkretnego pola; inne filtry gubione przy Load More -->
?offset={{ next_offset }}{% if request.GET.category %}&category={{ request.GET.category }}{% endif %}

<!-- AFTER: adapter serializuje pełen stan filtra; fixes lessons.md bug jednocześnie -->
?offset={{ next_offset }}{% if pref_filter.pagination_params %}&{{ pref_filter.pagination_params }}{% endif %}
```

#### `attractions/tests.py:5,103,107,113`

```python
# BEFORE: warstwa testów importuje adapter bezpośrednio, woła .qs
from attractions.filters import AttractionFilter

f = AttractionFilter({}, queryset=Attraction.objects.all())
self.assertEqual(f.qs.count(), 3)

# AFTER: testy filtrowania przez HTTP layer (brak importu AttractionFilter w tests.py)
response = self.client.get(reverse("attraction-list"))
self.assertEqual(len(response.context["attractions"]), 3)

response = self.client.get(reverse("attraction-list") + "?category=culture")
self.assertEqual(len(response.context["attractions"]), 2)
# Kontekst zwraca ActivePreferenceFilter, nie FilterSet
self.assertIsInstance(response.context["pref_filter"], ActivePreferenceFilter)
self.assertEqual(response.context["pref_filter"].selected_category, "culture")
```

### Warstwa UI dostaje gotowe dane domenowe, nie surowy obiekt biblioteki

| Zmienna w kontekście | Typ przed | Typ po |
|---|---|---|
| `filter` / `pref_filter` | `AttractionFilter` (django-filter FilterSet) | `ActivePreferenceFilter` (frozen dataclass) |
| `filter.form.as_p()` | woływane w szablonie — biblioteka w UI | `pref_filter.form_html` — gotowy `SafeString` |
| URL paginacji | template wątki `request.GET.category` ręcznie | `pref_filter.pagination_params` gotowy URL string |

---

## KROK 6 — Weryfikacja i plan faz

### Kryterium sukcesu — grep

```
# Po refaktorze — tylko te dwa pliki mogą zawierać "django_filters" lub "AttractionFilter":
grep -rn "django_filters\|AttractionFilter" attractions/
```

**Oczekiwany wynik po refaktorze**:

| Plik | Powinien matchować | Powód |
|---|---|---|
| `attractions/filters.py` | TAK | Adapter domenowy FilterSet — akceptowalne |
| `attractions/adapters.py` | TAK | Jedyny legalny import poza `filters.py` |
| `attractions/views.py` | **NIE** | Widok używa portu/adaptera, nie biblioteki |
| `attractions/tests.py` | **NIE** | Testy sprawdzają przez HTTP layer |
| `attractions/templates/**` | **NIE** | Szablony dostają domain VO |

**Aktualny stan** (przed refaktorem):

```
attractions/filters.py:1   import django_filters          ← adapter — OK
attractions/filters.py:6   class AttractionFilter(django_filters.FilterSet)
attractions/filters.py:7   django_filters.ChoiceFilter
attractions/views.py:5     from attractions.filters import AttractionFilter  ← PRZECIEK
attractions/views.py:12    f = AttractionFilter(request.GET, ...)            ← PRZECIEK
attractions/views.py:17    qs = f.qs                                         ← PRZECIEK
attractions/views.py:30    "filter": f                                       ← PRZECIEK do UI
attractions/tests.py:5     from attractions.filters import AttractionFilter  ← PRZECIEK
attractions/tests.py:103   f = AttractionFilter({}, ...)                     ← PRZECIEK
attractions/tests.py:107   f = AttractionFilter({"category": "culture"}, ...)← PRZECIEK
attractions/tests.py:113   f = AttractionFilter({"category": ""}, ...)       ← PRZECIEK
list.html:17               {{ filter.form.as_p }}                            ← PRZECIEK do UI
```

---

### Plan faz refaktoru

Projekt ma dyscyplinę TDD (mutmut, pytest-django, test runner: `uv run python manage.py test`).
Fazy 1 i 3 idą **test-first** — testy czerwone, potem implementacja.

#### Faza 1 — Domain Value Object + Port (bez zmian w views/tests)

| Krok | Działanie | Pliki |
|---|---|---|
| 1.1 | Dodaj `ActivePreferenceFilter` dataclass do `attractions/domain.py` | `domain.py` (dołącz) |
| 1.2 | Utwórz `attractions/ports.py` z `IPreferenceFilterBuilder` Protocol | nowy plik |
| 1.3 | Utwórz `attractions/adapters.py` z `DjangoFilterPreferenceFilterAdapter` | nowy plik |
| 1.4 | Napisz testy adaptera (nie testu widoku) — RED | `attractions/tests.py` (nowa klasa) |
| 1.5 | Zaimplementuj adapter — GREEN | `adapters.py` |

> **Test-first**: nowa klasa `PreferenceFilterAdapterTest` w `tests.py` sprawdza:
> - `adapter.build(QueryDict("")) → selected_category=None`
> - `adapter.build(QueryDict("category=culture")) → selected_category='culture'`
> - `adapter.build(QueryDict("category=bogus")) → selected_category='bogus'` (django-filter ignoruje)
> - `adapter.build(QueryDict("category=family&offset=6")) → pagination_params='category=family'` (bez offset)
> - `adapter.apply(QueryDict("category=culture"), qs).count() == tylko culture`

#### Faza 2 — Adapter w widoku (testy istniejące muszą przejść)

| Krok | Działanie | Pliki |
|---|---|---|
| 2.1 | Zastąp `AttractionFilter` adapterem w `attraction_list` | `attractions/views.py` |
| 2.2 | Zmień klucz kontekstu: `"filter"` → `"pref_filter"`, typ: `ActivePreferenceFilter` | `attractions/views.py:30` |
| 2.3 | Uruchom pełny test suite — wszystkie istniejące testy muszą przejść bez modyfikacji | `uv run python manage.py test` |

> Widok zmienia klucz kontekstu z `"filter"` na `"pref_filter"` — istniejące testy widoku
> (`AttractionListViewTest`) nie sprawdzają zawartości `filter` w kontekście, więc nie wymagają
> zmian. Sprawdź: `grep -n '"filter"' attractions/tests.py`.

#### Faza 3 — Szablony używają domain VO (test-first na poziomie HTTP)

| Krok | Działanie | Pliki |
|---|---|---|
| 3.1 | Napisz testy sprawdzające `response.context["pref_filter"]` — RED | `tests.py` |
| 3.2 | Zaktualizuj `list.html:17` → `{{ pref_filter.form_html }}` | `list.html` |
| 3.3 | Zaktualizuj `filter_results.html:19` → `pref_filter.pagination_params` | `filter_results.html` |
| 3.4 | Zaktualizuj `cards_append.html:15` → `pref_filter.pagination_params` | `cards_append.html` |
| 3.5 | Uruchom test suite — GREEN | `uv run python manage.py test` |

> Krok 3.3 i 3.4 jednocześnie naprawia bug z `lessons.md` (pełna serializacja params filtra
> bez couplingу szablonu z biblioteką).

#### Faza 4 — Usunięcie bezpośrednich importów AttractionFilter z tests.py

| Krok | Działanie | Pliki |
|---|---|---|
| 4.1 | Zastąp `AttractionFilterTest` testami przez HTTP layer | `attractions/tests.py:95-114` |
| 4.2 | Usuń `from attractions.filters import AttractionFilter` z `tests.py` | `attractions/tests.py:5` |
| 4.3 | Uruchom test suite — GREEN | `uv run python manage.py test` |

#### Faza 5 — Weryfikacja izolacji

```powershell
# Kryterium sukcesu: 0 wyników poza filters.py i adapters.py
Select-String -Path "attractions\*.py" -Pattern "django_filters|AttractionFilter" |
    Where-Object { $_.Filename -notin @("filters.py", "adapters.py") }
# Oczekiwane: brak wyników
```

---

### Nowe nazwy rejestrowane przez ACL

```
attractions.domain.ActivePreferenceFilter          — Value Object stanu filtra
attractions.ports.IPreferenceFilterBuilder         — Port domenowy (Protocol)
attractions.adapters.DjangoFilterPreferenceFilterAdapter — Adapter (jedyny import biblioteki)
```

### Pliki po refaktorze nie znające django-filter

```
attractions/views.py       ← usuwa import AttractionFilter
attractions/tests.py       ← usuwa import AttractionFilter (4 miejsca)
attractions/templates/**   ← przestają wołać filter.form.as_p
```

---
title: "corobimy — Invariant Aggregate Refactor Plan"
created: 2026-06-28
type: refactor-plan
source: context/domain/01-domain-distillation.md
---

# Invariant Aggregate Refactor Plan

## KROK 0 — Kontekst

### Stack i warstwy logiki

| Warstwa | Pliki | Rola |
|---|---|---|
| **Domain / Persystencja** | `attractions/models.py` | Encje, pola, meta-constraints |
| **Application** | `attractions/views.py`, `accounts/views.py` | Orkiestracja, auth-gate, redirect |
| **Query / Filter** | `attractions/filters.py` | Filtrowanie po kategorii (read-side) |
| **UI / Template** | `attractions/templates/**/*.html` | Render kart, wyświetlanie kategorii |
| **Admin** | `attractions/admin.py` | Operator CRUD |

Logika biznesowa nie ma oddzielnej warstwy serwisowej — żyje bezpośrednio w widokach Django.

---

## KROK 1 — Identyfikacja niezmienników biznesowych

### IN-01: Kategoria musi być z zamkniętego zbioru {family, couples, sport, culture}

> prd.md:94 — "assigns each Kraków attraction a category tag (family / couples / sport / culture)"
> prd.md:96 — "The categorization is the sole decision the product makes for the user"

Jeśli kategoria ma nieprawidłową wartość (np. `""`  lub `"invalid"`), atrakcja staje się
niewidoczna we wszystkich widokach z filtrem, ale widoczna bez filtra — **feed jest
niespójny**. Filtr `ChoiceFilter` po prostu nie dopasuje wartości spoza `CATEGORY_CHOICES`.

**Aktualna egzekucja**: walidacja formularza Django (form layer), brak DB constraint.

---

### IN-02: Atrakcja musi mieć jedną lub WIĘCEJ kategorii

> prd.md (shape-notes.md):110 — "assigns it **one or more** category tags"

Model ma jedno pole `category = CharField(...)`. Reprezentacja "jeden lub więcej" jest
strukturalnie **niemożliwa** w obecnym schemacie — atrakcja może mieć dokładnie jedną
kategorię. Niezmiennik jest naruszony samym kształtem modelu, a nie tylko brakiem walidacji.

**Aktualna egzekucja**: niemożliwa — model strukturalnie nie obsługuje multi-kategorialności.

---

### IN-03: Zapis należy wyłącznie do właściciela (izolacja użytkownika)

> prd.md:125 — "saved attractions are private to each user"

**Aktualna egzekucja**: Dobrze zabezpieczony — `request.user` w każdym zapytaniu, FK do
AUTH_USER_MODEL, test `UserSaveIsolationTest`. Nie wymaga refaktoru.

---

### IN-04: Użytkownik może zapisać daną atrakcję co najwyżej raz

> Implicit — "A saved attraction is persisted to the user's account" (singular).

**Aktualna egzekucja**: Dobrze zabezpieczony — `unique_together` na poziomie DB + `get_or_create`
w widoku. Nie wymaga refaktoru.

---

### IN-05: Zapis/cofnięcie zapisu wymaga uwierzytelnienia

> prd.md:108 — "Saving requires authentication."

**Aktualna egzekucja**: Dobrze zabezpieczony — `@login_required` na obu widokach. Nie wymaga
refaktoru.

---

### IN-06: Cofnięcie zapisu (unsave) jest ciche dla nieistniejącego zapisu

> Brak reguły w PRD — obecna implementacja używa `filter().delete()`.

`unsave_attraction` nigdy nie rzuca błędu domenowego — operacja na nieistniejącym zapisie
kończy się powodzeniem (HTTP 200) bez żadnego sygnału. To naruszenie zasady fail-fast dla
operacji domenowej. **Ryzyko niskie** (MVP), ale jest to pogwałcenie zasady "nielegalna
operacja zatrzymuje".

---

### IN-07: Feed nie zawiera nieaktualnych/zamkniętych atrakcji

> prd.md:43 — "Attraction data must be current and accurate: no stale listings for closed or
> non-existent venues. A user who shows up to a closed attraction based on the app's
> recommendation is a trust-destroying failure."

**Aktualna egzekucja**: kompletnie brak — żadnego pola `is_active`, `status`, `last_verified_at`.
Cały corpus pojawia się zawsze w feedzie, bez możliwości wycofania atrakcji. Wymaga osobnego
kroku (FR-009 + pole statusu), poza zakresem tego dokumentu.

---

## KROK 2 — Klasyfikacja i wybór #1

### Tabela ocen

| Niezmiennik | (a) Rdzeniowość | (b) Rozsianie po warstwach | (c) Egzekucja | Priorytet |
|---|---|---|---|---|
| **IN-01** Zamknięty zbiór kategorii | ★★★ Sole decision | 4 warstwy: model, filter, templates, admin | Tylko form-layer; bypassowalny | **WYSOKI** |
| **IN-02** Jedna lub więcej kategorii | ★★★ Sole decision + PRD "one or more" | Model strukturalnie błędny | **Niemożliwa** w obecnym schemacie | **NAJWYŻSZY** |
| IN-03 Izolacja zapisu | ★★★ Prywatność danych | 3 miejsca w views | Dobrze egzekwowany | Niski |
| IN-04 Unikalność zapisu | ★★★ Integralność | 2 miejsca | DB constraint | Niski |
| IN-05 Auth gate | ★★★ | 2 dekoratory | Dobrze egzekwowany | Niski |
| IN-06 Fail-fast unsave | ★ | 1 widok | Brak fail-fast | Średni |
| IN-07 Brak stale | ★★★ Trust guardrail | 0 warstw (brak pola) | Kompletny brak | Wysoki (osobny CR) |

### Wybrany niezmiennik #1

**IN-01 + IN-02 razem: "Atrakcja musi mieć jedną lub więcej kategorii, każda z zamkniętego
zbioru {family, couples, sport, culture}"**

To są dwa poziomy tego samego rdzeniowego niezmiennika:
- IN-01 (wartość poprawna) jest aktywny i bypassowalny przez ORM
- IN-02 (co najmniej jedna) jest niemożliwy do wyegzekwowania z obecnym schematem

**Uzasadnienie wyboru**:
- **Rdzeniowość**: prd.md wprost mówi "the categorization is the sole decision the product
  makes for the user" — bez poprawnej kategorii produkt nie ma sensu
- **Rozsianie**: `CATEGORY_CHOICES` pojawia się w 4 warstwach jako zwykła lista krotek — brak
  enkapsulacji, brak jedynego właściciela tej reguły
- **Egzekucja**: IN-01 egzekwowany tylko przez Django forms (Bypass: `Attraction.objects.create(
  name="X", category="bogus", description="Y")` — silently persists); IN-02 jest niereprezento-
  walny przez obecny schema → każde wywołanie pipeline'u kategoryzacji AI, które próbowałoby
  przypisać wiele kategorii, miałoby niezdefiniowane zachowanie

---

## KROK 3 — Diagnoza wybranego niezmiennika

### Gdzie dziś żyje reguła (kompletna mapa)

#### Warstwa DEFINICJA — `attractions/models.py:4-9`

```python
CATEGORY_CHOICES = [
    ('family', 'Families'),
    ('couples', 'Couples'),
    ('sport', 'Sport'),
    ('culture', 'Culture'),
]
```

Zwykła lista krotek na poziomie modułu. Nie jest typem, nie ma metod, nie ma żadnej logiki
walidacyjnej. Każdy moduł może zaimportować i użyć tej listy bez żadnej gwarancji poprawności.

#### Warstwa PRZECHOWYWANIA — `attractions/models.py:14`

```python
category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
```

`choices=` w Django to sygnał dla formularzy i `ModelForm` — NIE jest to constraint na
poziomie bazy danych. Bezpośredni zapis przez ORM:

```python
Attraction.objects.create(name="X", category="", description="Y")          # ← przechodzi
Attraction.objects.create(name="Y", category="invalid_val", description="") # ← przechodzi
Attraction.objects.update(category="bogus")                                  # ← przechodzi
```

Wszystkie powyższe instrukcje **kończą się sukcesem** bez żadnego błędu.

Brak `clean()` na modelu, brak `save()` override, brak `constraints = [CheckConstraint(...)]`.

#### Warstwa FILTROWANIA — `attractions/filters.py:4,8`

```python
from attractions.models import CATEGORY_CHOICES, Attraction

category = django_filters.ChoiceFilter(
    choices=CATEGORY_CHOICES,
    empty_label='All categories',
)
```

`ChoiceFilter` waliduje wartość po stronie odczytu (HTTP GET). Jeśli `?category=bogus`, filtr
zwraca pusty `QuerySet`. Jeśli w DB jest atrakcja z `category="bogus"`, nie pojawi się NIGDY
w żadnym widoku z aktywnym filtrem, ale pojawi się gdy filtr jest wyłączony.

#### Warstwa WYŚWIETLANIA — `filter_results.html:5`, `cards_append.html:3`

```
{{ attraction.get_category_display }}
```

`get_category_display()` zwraca etykietę z `CATEGORY_CHOICES`. Dla wartości spoza zbioru
zwraca samą wartość (np. `"bogus"`), co jest widoczne dla użytkownika. Brak fail-fast.

#### Warstwa ADMINISTRACJI — `attractions/admin.py:8-9`

```python
list_display = ('name', 'category')
list_filter = ('category',)
```

Django admin używa `ModelAdmin` z `ModelForm` — tutaj `choices=` jest egzekwowany przez
Django formularze. Jedyne miejsce, gdzie niepoprawna kategoria jest BLOKOWANA — ale wyłącznie
w UI admina.

### Podsumowanie: co nie egzekwuje reguły

| Ścieżka zapisu | Egzekwuje? | Dowód |
|---|---|---|
| Django Admin UI | TAK (form) | `ModelAdmin` uses `ModelForm` with `choices` validation |
| `Attraction.objects.create(...)` | NIE | Brak `full_clean()` w `Model.save()` |
| `Attraction.objects.update(...)` | NIE | `update()` nie wywołuje `clean()` |
| Data migration | NIE | Bezpośredni SQL, żaden hook modelu |
| Import przez management command | NIE | Zależy od kodu komendy |
| Przyszły pipeline kategoryzacji AI | NIE | Będzie używał ORM, nie formularzy |
| Test factory (`make_attraction()`) | NIE | `Attraction.objects.create(...)` w `tests.py:7-8` |

### Gdzie klient jest jedynym strażnikiem

Jedynym faktycznym strażnikiem niezmiennika jest **Django Admin UI** (form layer). To znaczy:
- Każda ścieżka zapisu POZA adminem jest niezabezpieczona
- Przyszły pipeline kategoryzacji AI będzie działał przez ORM → **niezmiennik będzie naruszony
  przy każdym autoimporcie atrakcji**
- Test factory nie waliduje kategorii → testy mogą maskować naruszenia niezmiennika

---

## KROK 4 — Projekt agregatu-strażnika

### 4.1 Value Object: `AttractionCategory`

`CATEGORY_CHOICES` jako lista krotek zastąpione typem. Własne metody: parsowanie z łańcucha,
generowanie `choices()` dla Django, wyświetlana etykieta.

```python
# attractions/domain.py  (NOWY PLIK)

import enum


class InvalidAttractionCategoryError(ValueError):
    """Raised when a category value is not in the closed set."""
    def __init__(self, value: str):
        valid = [c.value for c in AttractionCategory]
        super().__init__(
            f"'{value}' is not a valid AttractionCategory. "
            f"Valid values: {valid}"
        )


class MissingAttractionCategoryError(ValueError):
    """Raised when an Attraction is created or updated with no categories."""
    def __init__(self):
        super().__init__(
            "Attraction must have at least one category assigned."
        )


class AttractionCategory(str, enum.Enum):
    FAMILY  = 'family'
    COUPLES = 'couples'
    SPORT   = 'sport'
    CULTURE = 'culture'

    @classmethod
    def from_str(cls, value: str) -> 'AttractionCategory':
        """Parse from string. Raises InvalidAttractionCategoryError on unknown value."""
        try:
            return cls(value)
        except ValueError:
            raise InvalidAttractionCategoryError(value)

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Return Django-compatible choices list."""
        labels = {
            'family':  'Families',
            'couples': 'Couples',
            'sport':   'Sport',
            'culture': 'Culture',
        }
        return [(item.value, labels[item.value]) for item in cls]

    @classmethod
    def valid_values(cls) -> list[str]:
        return [item.value for item in cls]
```

### 4.2 Agregat-strażnik: `Attraction` + `AttractionCategoryTag`

**Faza 1 (bez zmiany schematu)**: Egzekucja na poziomie modelu przez `clean()` + `save()` +
DB `CheckConstraint`. Zachowuje pole `category` jako single-value.

**Faza 2 (zmiana schematu)**: Nowy model `AttractionCategoryTag` (M2M przez pośrednik) +
metody domenowe na agregacie.

Poniżej projekt Fazy 2 (cel docelowy):

```python
# attractions/models.py  (po refaktorze)

from django.conf import settings
from django.db import models

from attractions.domain import (
    AttractionCategory,
    InvalidAttractionCategoryError,
    MissingAttractionCategoryError,
)


class AttractionCategoryTag(models.Model):
    """
    One row per (Attraction, Category) pair.
    AttractionCategory.valid_values() drives the CheckConstraint —
    adding a new category to the enum automatically gates new tags.
    """
    attraction = models.ForeignKey(
        'Attraction',
        on_delete=models.CASCADE,
        related_name='category_tags',
    )
    category = models.CharField(
        max_length=20,
        choices=AttractionCategory.choices(),
        db_index=True,
    )

    class Meta:
        unique_together = [('attraction', 'category')]
        constraints = [
            models.CheckConstraint(
                check=models.Q(category__in=AttractionCategory.valid_values()),
                name='attraction_category_tag_valid_category',
            )
        ]

    def __str__(self) -> str:
        return self.category


class Attraction(models.Model):
    """
    Aggregate root for the Attraction context.
    All mutations go through factory (create) or set_categories —
    never through direct ORM writes to category_tags.
    """
    name        = models.CharField(max_length=200)
    description = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    # ------------------------------------------------------------------ #
    # Factory — single path to create a valid Attraction                  #
    # ------------------------------------------------------------------ #

    @classmethod
    def create(
        cls,
        *,
        name: str,
        categories: list[AttractionCategory],
        description: str,
    ) -> 'Attraction':
        """
        Preconditions:
          - categories is non-empty
          - every item is an AttractionCategory member

        Raises:
          MissingAttractionCategoryError  — if categories is empty
          InvalidAttractionCategoryError  — if any item is not a valid member
        """
        if not categories:
            raise MissingAttractionCategoryError()
        for cat in categories:
            if not isinstance(cat, AttractionCategory):
                raise InvalidAttractionCategoryError(str(cat))

        instance = cls(name=name, description=description)
        instance.save()  # get PK
        AttractionCategoryTag.objects.bulk_create([
            AttractionCategoryTag(attraction=instance, category=cat.value)
            for cat in categories
        ])
        return instance

    # ------------------------------------------------------------------ #
    # Domain method — replace all categories atomically                   #
    # ------------------------------------------------------------------ #

    def set_categories(self, categories: list[AttractionCategory]) -> None:
        """
        Replace all category tags in one transaction.

        Preconditions:
          - categories is non-empty
          - every item is an AttractionCategory member

        Raises:
          MissingAttractionCategoryError  — if categories is empty
          InvalidAttractionCategoryError  — if any item is not a valid member
        """
        if not categories:
            raise MissingAttractionCategoryError()
        for cat in categories:
            if not isinstance(cat, AttractionCategory):
                raise InvalidAttractionCategoryError(str(cat))

        with transaction.atomic():
            self.category_tags.all().delete()
            AttractionCategoryTag.objects.bulk_create([
                AttractionCategoryTag(attraction=self, category=cat.value)
                for cat in categories
            ])

    # ------------------------------------------------------------------ #
    # Query helper (read-only, no invariant responsibility)               #
    # ------------------------------------------------------------------ #

    def has_category(self, category: AttractionCategory) -> bool:
        return self.category_tags.filter(category=category.value).exists()

    def get_primary_category_display(self) -> str:
        """Return the display label of the first (alphabetically) category."""
        tag = self.category_tags.order_by('category').first()
        if tag is None:
            return ''
        cat = AttractionCategory(tag.category)
        return dict(AttractionCategory.choices())[cat.value]


class UserSavedAttraction(models.Model):
    """Unchanged — invariants IN-03/IN-04/IN-05 already well-enforced."""
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_attractions',
    )
    attraction = models.ForeignKey(
        Attraction,
        on_delete=models.CASCADE,
        related_name='saves',
    )
    saved_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'attraction')]
        ordering        = ['-saved_at']

    def __str__(self) -> str:
        return f"{self.user} → {self.attraction}"
```

### 4.3 Repozytorium

```python
# attractions/repository.py  (NOWY PLIK)

from django.db.models import QuerySet, Prefetch

from attractions.domain import AttractionCategory
from attractions.models import Attraction, AttractionCategoryTag


class AttractionRepository:
    """
    Single gateway for Attraction reads/writes.
    Hides ORM details from views; enforces use of aggregate methods.
    """

    def list_for_feed(
        self,
        category: AttractionCategory | None = None,
    ) -> QuerySet:
        """
        Return attractions for the browse feed, optionally filtered
        by a single category. Prefetches category_tags to avoid N+1.
        """
        qs = Attraction.objects.prefetch_related(
            Prefetch('category_tags', queryset=AttractionCategoryTag.objects.order_by('category'))
        )
        if category is not None:
            qs = qs.filter(category_tags__category=category.value)
        return qs

    def get_or_404(self, pk: int) -> Attraction:
        from django.shortcuts import get_object_or_404
        return get_object_or_404(Attraction, pk=pk)

    def create(
        self,
        *,
        name: str,
        categories: list[AttractionCategory],
        description: str,
    ) -> Attraction:
        """Single creation path through the aggregate factory."""
        return Attraction.create(
            name=name,
            categories=categories,
            description=description,
        )
```

### 4.4 Cienkie API / widok

```python
# attractions/views.py  (po refaktorze — fragment attraction_list)

from attractions.domain import AttractionCategory, InvalidAttractionCategoryError
from attractions.repository import AttractionRepository

_repo = AttractionRepository()

def attraction_list(request):
    raw_category = request.GET.get('category', '')
    try:
        category = AttractionCategory.from_str(raw_category) if raw_category else None
    except InvalidAttractionCategoryError:
        category = None  # nieznana wartość → treat as "all"

    try:
        offset = max(0, int(request.GET.get("offset", 0)))
    except (ValueError, TypeError):
        offset = 0

    qs    = _repo.list_for_feed(category=category)
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

    # ... rest unchanged
```

> **Kluczowa zmiana**: widok nie waliduje kategorii — deleguje do `AttractionCategory.from_str()`.
> Walidacja przenosi się z `ChoiceFilter` (request-side) na Value Object (domain-side). Widok
> obsługuje błąd, ale egzekucja reguły siedzi w domenie.

### 4.5 Atomowość `set_categories`

Metoda `set_categories` opakowuje delete + bulk_create w `transaction.atomic()`. Częściowa
aktualizacja (np. wyjątek w połowie bulk_create) cofa całą operację — agregat nigdy nie
pozostaje w stanie z "0 kategorii".

---

## KROK 5 — Before / After, plan faz, testy

### Before / After dla każdego miejsca reguły

#### `attractions/models.py:4-9`

```python
# BEFORE
CATEGORY_CHOICES = [('family', 'Families'), ('couples', 'Couples'), ...]

# AFTER
# (usunięte — przeniesione do attractions/domain.py jako AttractionCategory enum)
```

#### `attractions/models.py:14`

```python
# BEFORE
category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

# AFTER — Faza 1 (bez zmiany schematu)
category = models.CharField(
    max_length=20,
    choices=AttractionCategory.choices(),
    constraints=[
        models.CheckConstraint(
            check=models.Q(category__in=AttractionCategory.valid_values()),
            name='attraction_valid_category',
        )
    ]
)
# + override save() i clean() na modelu

# AFTER — Faza 2 (pełny refaktor)
# Pole category usunięte → zastąpione relacją do AttractionCategoryTag
```

#### `attractions/filters.py:4,8`

```python
# BEFORE
from attractions.models import CATEGORY_CHOICES, Attraction
category = django_filters.ChoiceFilter(choices=CATEGORY_CHOICES, ...)

# AFTER — Faza 1
from attractions.domain import AttractionCategory
category = django_filters.ChoiceFilter(choices=AttractionCategory.choices(), ...)

# AFTER — Faza 2
# ChoiceFilter zastąpiony własną metodą filtrującą przez category_tags
category = django_filters.ChoiceFilter(
    choices=AttractionCategory.choices(),
    method='filter_by_category_tag',
)

def filter_by_category_tag(self, queryset, name, value):
    return queryset.filter(category_tags__category=value)
```

#### `attractions/admin.py:8-9`

```python
# BEFORE
list_display = ('name', 'category')
list_filter  = ('category',)

# AFTER — Faza 2
list_display = ('name', 'get_categories_display')
list_filter  = ('category_tags__category',)
# + inline: AttractionCategoryTagInline
```

#### `filter_results.html:5`, `cards_append.html:3`

```html
<!-- BEFORE -->
{{ attraction.get_category_display }}

<!-- AFTER — Faza 1: bez zmian -->
{{ attraction.get_category_display }}

<!-- AFTER — Faza 2 -->
{% for tag in attraction.category_tags.all %}
  {{ tag.get_category_display }}{% if not forloop.last %}, {% endif %}
{% endfor %}
```

#### `attractions/tests.py:7-8` (test factory)

```python
# BEFORE
def make_attraction(name, category="culture", description="Test description"):
    return Attraction.objects.create(name=name, category=category, description=description)

# AFTER — Faza 1: brak zmian (string nadal akceptowany przez choices)

# AFTER — Faza 2: użycie agregatu, nie ORM
from attractions.domain import AttractionCategory

def make_attraction(name, categories=None, description="Test description"):
    if categories is None:
        categories = [AttractionCategory.CULTURE]
    return Attraction.create(name=name, categories=categories, description=description)
```

---

### Plan faz refaktoru

#### Faza 1 — Egzekucja niezmiennika bez zmiany schematu

> **Cel**: Natychmiastowe zamknięcie dziury. ORM nie może już zapisać niedozwolonej kategorii.
> Nie wymaga migracji danych.

| Krok | Działanie | Pliki |
|---|---|---|
| 1.1 | Utwórz `attractions/domain.py` z `AttractionCategory` enum + błędy domenowe | nowy plik |
| 1.2 | Zastąp `CATEGORY_CHOICES` odwołaniami do `AttractionCategory.choices()` w `models.py` | `models.py:4-14` |
| 1.3 | Dodaj `clean()` + `save(self.full_clean)` + `CheckConstraint` do modelu `Attraction` | `models.py:18-30` |
| 1.4 | Wygeneruj i zastosuj migrację (tylko CheckConstraint) | `migrations/` |
| 1.5 | Zaktualizuj `filters.py` — import z `domain.py` zamiast z `models.py` | `filters.py:4` |
| 1.6 | Zaktualizuj test factory `make_attraction()` — nieopacjonalny string przez `AttractionCategory.CULTURE` | `tests.py:7-8` |

> **Test-first** — Faza 1 idzie RED → GREEN:
> - Napisz testy (patrz sekcja testów niżej) → czerwone
> - Wykonaj kroki 1.1–1.4 → testy zielone

#### Faza 2 — Multi-category schema + agregat pełny

> **Cel**: Dostosowanie modelu do PRD ("one or more category tags"). Wymaga migracji danych.

| Krok | Działanie | Pliki |
|---|---|---|
| 2.1 | Utwórz `AttractionCategoryTag` model (FK do Attraction + CheckConstraint) | `models.py` |
| 2.2 | Dodaj metody domenowe `Attraction.create()` i `Attraction.set_categories()` | `models.py` |
| 2.3 | Migracja danych: skopiuj istniejące wartości `category` → wiersze `AttractionCategoryTag` | `migrations/` |
| 2.4 | Migracja schematu: usuń pole `category` z `Attraction` | `migrations/` |
| 2.5 | Utwórz `attractions/repository.py` z `AttractionRepository` | nowy plik |
| 2.6 | Zaktualizuj `filters.py` → `filter_by_category_tag` method | `filters.py` |
| 2.7 | Zaktualizuj `views.py` → użyj `AttractionRepository.list_for_feed()` | `views.py` |
| 2.8 | Zaktualizuj `admin.py` → `AttractionCategoryTagInline` + `list_filter` | `admin.py` |
| 2.9 | Zaktualizuj szablony → iteruj `category_tags.all` | `filter_results.html`, `cards_append.html` |
| 2.10 | Zaktualizuj test factory → `Attraction.create(categories=[...])` | `tests.py` |

> **Test-first** — Faza 2 idzie RED → GREEN:
> - Napisz nowe testy (agregat + wielokrotne kategorie) → czerwone
> - Wykonaj kroki 2.1–2.10 → testy zielone

---

### Przypadki testowe dla niezmiennika

#### Operacje legalne (muszą przejść)

```python
# L-01: Tworzenie z jedną prawidłową kategorią
Attraction.create(
    name="Wawel Castle",
    categories=[AttractionCategory.CULTURE],
    description="Historic castle",
)
# Oczekiwane: obiekt zapisany, category_tags.count() == 1

# L-02: Tworzenie z wieloma prawidłowymi kategoriami (Faza 2)
Attraction.create(
    name="Family Sport Centre",
    categories=[AttractionCategory.FAMILY, AttractionCategory.SPORT],
    description="For families who love sport",
)
# Oczekiwane: category_tags.count() == 2

# L-03: set_categories zastępuje istniejące tagi atomowo (Faza 2)
attraction.set_categories([AttractionCategory.CULTURE, AttractionCategory.COUPLES])
# Oczekiwane: poprzednie tagi usunięte, nowe dodane; count == 2

# L-04: Filtr zwraca tylko atrakcje z daną kategorią
qs = repo.list_for_feed(category=AttractionCategory.SPORT)
# Oczekiwane: wszystkie obiekty w qs mają tag SPORT

# L-05: Filtr None zwraca wszystkie atrakcje (bez filtrowania)
qs = repo.list_for_feed(category=None)
# Oczekiwane: qs.count() == Attraction.objects.count()

# L-06: AttractionCategory.from_str('family') zwraca AttractionCategory.FAMILY
cat = AttractionCategory.from_str('family')
assert cat is AttractionCategory.FAMILY
```

#### Operacje nielegalne (muszą zatrzymać, nie logować)

```python
# I-01: Tworzenie bez kategorii → MissingAttractionCategoryError
with pytest.raises(MissingAttractionCategoryError):
    Attraction.create(name="X", categories=[], description="Y")

# I-02: Tworzenie z nieznaną kategorią → InvalidAttractionCategoryError
with pytest.raises(InvalidAttractionCategoryError):
    Attraction.create(name="X", categories=["unknown"], description="Y")

# I-03: set_categories z pustą listą → MissingAttractionCategoryError (Faza 2)
with pytest.raises(MissingAttractionCategoryError):
    attraction.set_categories([])

# I-04: Bezpośredni ORM z błędną kategorią → IntegrityError (CheckConstraint)
with pytest.raises(IntegrityError):
    AttractionCategoryTag.objects.create(
        attraction=some_attraction, category="bogus"
    )

# I-05: AttractionCategory.from_str z nieznaną wartością → InvalidAttractionCategoryError
with pytest.raises(InvalidAttractionCategoryError):
    AttractionCategory.from_str('INVALID')

# I-06: Faza 1 — model.save() z błędną kategorią → ValidationError
attraction = Attraction(name="X", category="bogus", description="Y")
with pytest.raises(ValidationError):
    attraction.save()
```

#### Test atomowości `set_categories` (Faza 2)

```python
# I-07: Wyjątek podczas set_categories → rollback, stare tagi zachowane
original_categories = [AttractionCategory.FAMILY]
attraction = Attraction.create(name="X", categories=original_categories, description="Y")

with mock.patch.object(AttractionCategoryTag.objects, 'bulk_create', side_effect=Exception("DB fail")):
    with pytest.raises(Exception):
        attraction.set_categories([AttractionCategory.CULTURE])

# Stare tagi muszą pozostać niezmienione
assert attraction.category_tags.filter(category='family').exists()
assert attraction.category_tags.count() == 1
```

---

### Nowe nazwy do zarejestrowania (load-bearing contracts)

```
attractions.domain.AttractionCategory         — Value Object, zamknięty zbiór kategorii
attractions.domain.InvalidAttractionCategoryError  — błąd domenowy: zła wartość
attractions.domain.MissingAttractionCategoryError  — błąd domenowy: brak kategorii
attractions.models.AttractionCategoryTag       — join model dla kategorii (Faza 2)
attractions.models.Attraction.create()         — jedyna legalna ścieżka tworzenia
attractions.models.Attraction.set_categories() — jedyna legalna ścieżka zmiany kategorii
attractions.repository.AttractionRepository   — gateway read/write do agregatu
```

---

## Uwagi implementacyjne

1. **Kolejność migracji w Fazie 2**: najpierw utwórz `AttractionCategoryTag` i skopiuj dane
   (data migration), potem usuń pole `category` z `Attraction`. Nigdy odwrotnie.

2. **Faza 1 jest bezpieczna do wdrożenia osobno**: CheckConstraint na istniejącym polu `category`
   zablokuje wyłącznie przyszłe nieprawidłowe zapisy. Istniejące dane w DB są prawidłowe (admin
   walidował je do tej pory).

3. **Faza 2 wymaga backward-compatible migration**: przed deployment Fazy 2 upewnij się, że
   żaden kod produkcyjny nie zapisuje do `Attraction.category` (Django deployment sequence:
   deploy kod obsługujący oba pola → migration → deploy kod usuwający stare pole).

4. **`Attraction.objects.update(category=...)` zostaje permanently removed** po Fazie 2 — każda
   zmiana kategorii musi przejść przez `set_categories()`.

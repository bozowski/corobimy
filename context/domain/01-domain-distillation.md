---
title: "corobimy — Domain Distillation"
created: 2026-06-28
type: domain-distillation
sources:
  - context/foundation/prd.md
  - context/foundation/shape-notes.md
  - idea-notes.md
  - context/foundation/tech-stack.md
  - context/changes/browse-first-save/plan.md
  - attractions/models.py
  - attractions/views.py
  - attractions/filters.py
  - accounts/views.py
---

# corobimy — Mapa Domeny (Domain Distillation)

## KROK 0 — Kontekst projektu

### Cel produktu

**corobimy** (pl. "co robimy?" = "what are we doing?") to webowa aplikacja discovery atrakcji
krakowskich. Rozwiązuje lukę odkrycia (_discovery gap_): turystom i mieszkańcom Krakowa
brakuje jednego miejsca agregującego aktualne propozycje dopasowane do ich preferencji.
Wyróżnikiem produktu jest kategoryzacja atrakcji (AI-assisted w wizji, ręczna w MVP) i
browse-first UX — użytkownik może przeglądać bez rejestracji, a auth jest wymagana dopiero
przy próbie zapisania atrakcji.

### Stack i struktura

- **Framework**: Django 6.x + PostgreSQL
- **Package manager**: uv
- **UI**: szablony Django + HTMX (offset pagination, partial swaps)
- **Deployment**: Railway (zalecany), Fly.io (fallback)

### Warstwy logiki

| Warstwa | Ścieżka | Rola |
|---|---|---|
| Domain/Persystencja | `attractions/models.py` | Encje i ich niezmienniki |
| Application | `attractions/views.py`, `accounts/views.py` | Orkiestracja, auth-gate |
| Query/Filter | `attractions/filters.py` | Filtrowanie po kategorii |
| UI | `attractions/templates/` | Renderowanie kart, partial HTMX |

> **Uwaga**: Brak oddzielnej warstwy serwisu. Logika biznesowa żyje bezpośrednio w widokach
> Django. To akceptowalne dla MVP, ale jest punktem uwagi przy skalowaniu.

---

## KROK 1 — Ubiquitous Language

### Terminy domenowe (z cytowanymi źródłami)

| Termin | Definicja | Źródło (dokument) | Miejsce w kodzie |
|---|---|---|---|
| **Attraction** (Atrakcja) | Miejsce lub wydarzenie w Krakowie dostępne do odkrycia | prd.md:70 "curated Kraków attractions" | `attractions/models.py:12` — `class Attraction` |
| **Category** (Kategoria) | Tag klasyfikacyjny atrakcji: `family` / `couples` / `sport` / `culture` | prd.md:94 "assigns each Kraków attraction a category tag" | `attractions/models.py:4-9` — `CATEGORY_CHOICES` |
| **Preference Filter** (Filtr Preferencji) | Opcjonalny filtr ustawiany przez użytkownika; zawęża feed do jednej kategorii | prd.md:68 "optionally filtering by preference"; FR-003 | `attractions/filters.py:6` — `AttractionFilter` |
| **Attraction Feed** (Feed Atrakcji) | Paginowana lista atrakcji widoczna dla każdego użytkownika | prd.md:47 "browse the attractions feed" | `attractions/views.py:11` — `attraction_list` |
| **Corpus** (Korpus Atrakcji) | Zbiór wszystkich dostępnych atrakcji w systemie | prd.md:98 "the current corpus" | BRAK w kodzie — brak abstrakcji, jedynie `Attraction.objects.all()` w `views.py:12` |
| **Save** (Zapis) | Akcja zalogowanego użytkownika oznaczającego atrakcję jako wybraną/ulubioną | prd.md FR-005 "User can select (save) an attraction" | `attractions/views.py:44-50` — `save_attraction` |
| **Unsave** (Cofnięcie zapisu) | Akcja cofająca wcześniejszy zapis | BRAK explicite w prd.md (nie wymienione jako FR) | `attractions/views.py:53-67` — `unsave_attraction` |
| **Saved Attraction** | Relacja pomiędzy użytkownikiem a atrakcją, rejestruje fakt zapisu | prd.md:57 "A saved attraction is persisted to the user's account" | `attractions/models.py:25` — `class UserSavedAttraction` |
| **Browse-first Pattern** | Wzorzec UX: przeglądanie bez logowania, auth wymagana tylko przy zapisie | prd.md:63 "unauthenticated users can browse; sign-up is prompted only when they attempt to save" | `attractions/views.py:44` — brak dekoratora na `attraction_list`, `@login_required` na `save_attraction` |
| **Categorization** (Kategoryzacja) | Proces przypisania tag(ów) kategorii do atrakcji na podstawie jej treści | prd.md (shape-notes.md):110 "AI reads each attraction's content and assigns it one or more category tags" | BRAK w kodzie — kategoria ustawiana ręcznie przez Django admin |
| **Seed Data** (Dane Startowe) | Zestaw ręcznie przygotowanych atrakcji krakowskich, gwarantujący niepusty feed od dnia 1 | prd.md:54 "seed data ensures non-empty initial state" | BRAK fixture file; tylko przez Django admin |
| **Operator Content Refresh** | Ręcznie wyzwalany przez operatora proces aktualizacji listy atrakcji | prd.md FR-009 "Operator can manually trigger a refresh" | BRAK w kodzie — niezaimplementowane |
| **Rejection / Dismiss** (Odrzucenie) | Akcja użytkownika oznaczająca atrakcję jako niechcianą; ma nie pojawiać się ponownie | prd.md FR-006 (nice-to-have, zdemotowane) | BRAK w kodzie — brak modelu i widoku |
| **History View** (Historia) | Dedykowany widok zapisanych atrakcji użytkownika | prd.md FR-008 (nice-to-have, zdemotowane) | BRAK widoku; dane `UserSavedAttraction` istnieją |
| **Page Size** | Liczba atrakcji zwracanych w jednej partii feedu (= 6) | BRAK w dokumentach wymagań | `attractions/views.py:8` — `PAGE_SIZE = 6` |
| **saved_pks** | Zbiór ID atrakcji zapisanych przez bieżącego użytkownika na aktualnej stronie | BRAK w dokumentach — termin implementacyjny | `attractions/views.py:22` — `saved_pks` w kontekście widoku |

---

## KROK 2 — Klasyfikacja subdomen

| Subdomena | Kategoria | Uzasadnienie |
|---|---|---|
| **Attraction Corpus + Categorization** | **Core** | To jest "core bet" produktu. prd.md (shape-notes.md):26-27: "AI makes it cheap to aggregate local Kraków sources and match a person's preferences in real time. This capability wasn't practically available before LLMs." Bez kategoryzacji nie ma przewagi. |
| **Preference Filter → Feed** | **Core** | prd.md:96: "The categorization is the sole decision the product makes for the user." Filtr i feed to główny interfejs tej decyzji. Powiązany bezpośrednio z success criteria (≥20% save rate). |
| **Save / Unsave** | **Core** | Jedyny mierzalny success metric (primary): prd.md:38 "≥ 20% of users who browse the attraction list actually select (save) at least one attraction per session." Bez save nie ma wskaźnika sukcesu. |
| **Browse-first Auth Pattern** | **Supporting** | Niezbędna do persystencji saves i ochrony danych. Interesujący wzorzec UX (opóźniony auth-gate), ale auth sama w sobie nie jest przewagą. prd.md:102-108 opisuje ją jako "gateway to persistence, not to the app." |
| **Operator Content Refresh** | **Supporting** | Potrzebna do aktualności danych (guardrail: prd.md:43 "stale listings for closed venues is a trust-destroying failure"), ale jest procesem operacyjnym, nie domenowym. |
| **Django Admin** | **Generic** | Standardowe narzędzie CRUD. Nie ma specyfiki domenowej — jedyne zastosowanie to ręczne zarządzanie korpusem atrakcji i userami. |
| **HTMX Pagination + Partials** | **Generic** | UI delivery mechanism. Implementuje offset pagination i partial swaps. Brak logiki domenowej. |
| **Infrastructure (Railway/Postgres)** | **Generic** | Infrastruktura. Żadnych decyzji domenowych. |

---

## KROK 3 — Kandydaci na agregaty i niezmienniki

### Kandydat 1: `Attraction`

**Niezmiennik I**: Każda atrakcja musi mieć przypisaną co najmniej jedną kategorię z zamkniętego zbioru
`{family, couples, sport, culture}`.

> Źródło: prd.md:94 "assigns each Kraków attraction a category tag (family / couples / sport /
> culture)"; shape-notes.md:110 "assigns it one or more category tags."

| Aspekt | Status |
|---|---|
| Kod deklaruje | `attractions/models.py:14` — `CharField(max_length=20, choices=CATEGORY_CHOICES)` |
| Kod egzekwuje | **Częściowo** — `choices` to walidacja Django formularza/serializera, nie constraint DB. Bezpośredni zapis przez ORM (`Attraction.objects.create(category='invalid')`) nie zostanie zablokowany. |
| Pominięty aspekt | Model mówi "one or more" w dokumentacji, ale pole `category` przechowuje dokładnie jedną wartość. Wielokrotne kategorie są ignorowane w modelu. |

**Niezmiennik II**: Nazwa atrakcji nie może być pusta.

> Źródło: prd.md implicit (atrakcja musi być identyfikowalna).

| Aspekt | Status |
|---|---|
| Kod egzekwuje | `attractions/models.py:13` — `CharField(max_length=200)` — Django domyślnie `blank=False`, ale brak `db_constraint`. |

---

### Kandydat 2: `UserSavedAttraction`

**Niezmiennik I**: Użytkownik może zapisać daną atrakcję co najwyżej raz (relacja unikalna).

> Źródło: prd.md FR-005 (implicit — "saved to the user's account", liczba pojedyncza).

| Aspekt | Status |
|---|---|
| Kod egzekwuje | **Tak** — `attractions/models.py:31` — `unique_together = [('user', 'attraction')]` + migration constraint na poziomie DB. `views.py:49` — `get_or_create` gwarantuje idempotentność. |

**Niezmiennik II**: Tylko uwierzytelniony użytkownik może zapisać atrakcję.

> Źródło: prd.md:108 "Saving requires authentication."

| Aspekt | Status |
|---|---|
| Kod egzekwuje | **Tak** — `attractions/views.py:44` — `@login_required` na `save_attraction`. |

**Niezmiennik III**: Cofnięcie zapisu (`unsave`) nie może naruszać zapisów innego użytkownika.

> Źródło: prd.md:125 "saved attractions are private to each user."

| Aspekt | Status |
|---|---|
| Kod egzekwuje | **Tak** — `attractions/views.py:57` — `filter(user=request.user, attraction=attraction).delete()` jawnie filtruje po `request.user`. Potwierdzone testem `UserSaveIsolationTest`. |

---

### Kandydat 3: `User` (Django built-in)

**Niezmiennik**: Unikalność nazwy użytkownika (username).

> Źródło: prd.md FR-001/002.

| Aspekt | Status |
|---|---|
| Kod egzekwuje | **Tak** — Django `AbstractUser` + `UserCreationForm`. |

> **Uwaga**: Brak dedykowanej encji `UserProfile` w domenie. Preferencja użytkownika (filtr)
> nie jest persystowana — jest przekazywana jako parametr URL (`?category=family`) i nie
> zapisuje się między sesjami. To jest luka między modelem mentalnym ("user sets a preference")
> a implementacją (request-scoped filter).

---

## KROK 4 — Rozjazdy MODEL vs KOD

| # | Dokument mówi (co/gdzie) | Kod robi | Dowód (plik:linia) |
|---|---|---|---|
| **D-1** | "assigns each Kraków attraction **one or more** category tags" | Model ma dokładnie JEDNO pole `category` — single-value CharField | prd.md (shape-notes.md):110 vs. `attractions/models.py:14` |
| **D-2** | "categorization pipeline" / "AI reads each attraction's content and assigns it category tags" (must-have technologicznie per prd.md:94) | Brak kodu kategoryzacji. Kategoria ustawiana ręcznie w Django admin | prd.md:94, brak pliku kategoryzacji |
| **D-3** | FR-009: "Operator can manually trigger a refresh of Kraków attraction listings" — **must-have** | Brak view/command/management-command do refreshu. Wyłącznie Django admin CRUD | prd.md:84 FR-009 vs. brak kodu |
| **D-4** | "preference filter" (FR-003) — "User can set a preference filter" (implicitly persisted per-user) | Filtr jest request-scoped parametrem URL (`?category=`), nie persystowanym profilem użytkownika | prd.md:68 FR-003 vs. `attractions/filters.py:6-14` |
| **D-5** | FR-006: "User can reject (dismiss) an attraction so it does not reappear" | Brak `UserRejectedAttraction` modelu i brak filtrowania "dismissed" z feedu | prd.md:76 FR-006 vs. brak kodu |
| **D-6** | US-01 AC: "At least one attraction is visible immediately — seed data ensures non-empty initial state" | Brak pliku fixture. Seed wyłącznie przez ręczny import w Django admin | prd.md:54 vs. brak `fixtures/` |
| **D-7** | NFR: "attraction list is visible within 2 seconds" | Brak indeksu DB na polu `category` — każdy filtr to full-table scan | prd.md:89 vs. `attractions/migrations/0001_initial.py:14-26` |
| **D-8** | "Unsave" nie jest wymienione w żadnym FR prd.md | `unsave_attraction` zaimplementowane jako w pełni działający endpoint POST `/attractions/<pk>/unsave/` | prd.md (brak FR) vs. `attractions/views.py:53-67`, `attractions/urls.py:8` |
| **D-9** | FR-007: "User can search attractions by free-text keyword" (nice-to-have) | `AttractionFilter` obsługuje tylko filtr kategorii; brak pola `search` | prd.md:78 FR-007 vs. `attractions/filters.py:6-14` |
| **D-10** | "The attraction corpus is populated and refreshed through an operator-initiated process. The app reads from the current corpus; it does not schedule or trigger refreshes autonomously." | `Attraction.objects.all()` w `attraction_list` czyta cały corpus bez żadnego mechanizmu aktualizacji | prd.md:98-99 vs. `attractions/views.py:12` |

---

## KROK 5 — Ranking refaktoru

Kryteria oceny:
- **Wartość**: jak blisko rdzenia domenowego (Core subdomain) leży problem
- **Ryzyko**: jak poważnie dziś brakuje egzekucji niezmiennika lub jak daleko model od dokumentu

### Ranking

| Poz. | Kandydat | Rozjazd | Wartość | Ryzyko | Uzasadnienie |
|---|---|---|---|---|---|
| **#1** | Multi-category (wiele kategorii) | D-1 | Krytyczna | Wysoka | PRD wprost mówi "one or more category tags" — to jest rdzeń decyzji produktu. Obecny model `CharField(category)` pozwala na dokładnie jedną wartość, co uniemożliwi w przyszłości filtrowanie cross-kategorialne (np. "family AND culture"). To nie jest kosmetyczny dług — to błąd w modelu domenowym. Refaktor: `ManyToManyField` do `Category` lub osobna tabela `AttractionCategory`. |
| **#2** | Operator Content Refresh (FR-009) | D-3 | Wysoka | Wysoka | must-have per PRD, całkowicie niezaimplementowane. Guardrail: "stale listings for a closed venue is a trust-destroying failure." Bez tego corpus starzeje się bez mechanizmu aktualizacji. |
| **#3** | Brak Seed Fixture | D-6 | Wysoka | Średnia | Acceptance Criteria US-01 wymaga niepustego feedu od dnia 1. Nowy deployment wymaga ręcznej interwencji operatora, co blokuje automację CI/CD i Railway auto-deploy. Tani fix: Django fixture `fixtures/initial_attractions.json`. |
| **#4** | Preference nie persystowana | D-4 | Średnia | Średnia | Użytkownik musi za każdą sesją na nowo ustawiać filtr. PRD FR-003 mówi "user can **set** a preference filter" co sugeruje trwałe ustawienie, nie jednorazowy filtr. Wymaga pola `preferred_category` na User lub profilu. |
| **#5** | Brak indeksu DB na `category` | D-7 | Średnia | Niska | NFR 2 sekundy. Przy małym zbiorze (seed MVP) nie ma problemu, ale tabela bez indeksu to pułapka przy skalowaniu korpusu. Jednolinijkowy fix w migracji. |

---

### Kandydat #1 do refaktoru: Multi-category model

**Dlaczego #1**: Kategoryzacja jest "the sole decision the product makes for the user" (prd.md:96).
Obecny model `CharField(category)` zapisuje jedną wartość, podczas gdy dokument mówi "one or
more category tags." Jeśli ta rozbieżność nie zostanie naprawiona przed wdrożeniem pipeline'u
kategoryzacji, każde rozszerzenie (np. atrakcja "rodzinna I kulturalna") wymagać będzie migracji
danych, nie tylko dodania kodu. To jest niezmiennik domenowy reprezentowany przez błędny typ
danych — najwyższa kategoria długu domenowego.

**Proponowany kierunek**:
```
Attraction (1) ──< AttractionCategory >── Category
```
lub krócej: `ManyToManyField(Category, related_name='attractions')` w modelu `Attraction`.

---

## Podsumowanie ograniczeń analizy

- **Kategorizacja AI** opisana w vision i shape-notes.md jako kluczowy element produktu jest
  całkowicie nieobecna w kodzie. Analiza opiera się na dokumentach i jest tu największa luka.
- Brak dedykowanej warstwy serwisowej oznacza, że wszystkie niezmienniki egzekwowane są przez
  widoki (HTTP layer) lub ORM constraints, co jest akceptowalne dla MVP ale ogranicza
  testowalność logiki domenowej bez warstwy HTTP.
- Filtr preferencji (`?category=`) jest implementacyjnie poprawny dla MVP, ale mentalny model
  "użytkownik ustawia preferencję" z PRD sugeruje persystencję.

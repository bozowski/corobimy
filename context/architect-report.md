---
title: "Moduł 4 — Raport architektoniczny (10xArchitect)"
created: 2026-06-28
type: architect-report
---

# Raport architektoniczny — Moduł 4

---

## 1. Opisane projekty

| Repo | Stack | Skala | Artefakty |
|---|---|---|---|
| **tldraw** | TypeScript, React, Yarn monorepo, Cloudflare Workers, zero-cache (Fly.io), Supabase | Duże — 272 moduły w jednym podgrafie `apps/dotcom`, 1251 commitów w roku, kilku aktywnych kontrybutorów | L2 (mapa), L3 (research), L4 (plan) |
| **corobimy** | Python 3.13, Django 6.x, PostgreSQL, HTMX, Railway, solo MVP | Małe — 2 aplikacje Django (`attractions/`, `accounts/`), 27 plików `.py` poza venv, jeden deweloper | L5 (DDD) |

Artefakty L2–L4 dotyczą wyłącznie tldraw. Artefakty L5 dotyczą wyłącznie corobimy.

---

## 2. Mapa projektu (L2 — tldraw)

**Kluczowe wnioski z repo-map.md:**

1. **Korzeń cykli** — `analytics.tsx` (Ca=21) importuje `useApp()` z warstwy domenowej (`useAppState.tsx`). Infrastruktura zna domenę. Jeden import generuje 3 cykle obejmujące 3–7 węzłów. *(źródło: graf importów dependency-cruiser, 272 moduły)*

2. **Hub z churnem** — `TlaEditor.tsx` Ce=33 importuje 33 lokalne moduły przy 47 commitach w roku. Równoległa praca kilku osób na UX generuje ryzyko konfliktów merge.

3. **Backend bez testów jednostkowych** — `sync-worker` + `dotcom-shared/src/types.ts` to żywy kontrakt backend↔frontend zmieniany 32× razem, ale Durable Objects wymagają runtime CF Workers; Miniflare nie jest skonfigurowany.

4. **Singleton blokujący testy** — `globalEditor` importowany przez 17 komponentów `tla/` bez `TestWrapper`; test bez inicjalizacji = crash. Skutek: ślepa plamka testowa całej warstwy UI `tla/`.

5. **Unknown w grafie** — dependency-cruiser objął wyłącznie `apps/dotcom/client` i `sync-worker`. Zależności wewnątrz `packages/*`, `zero-cache` i `apps/docs` są **nieznane** — brak grafu ≠ brak powiązań.

---

## 3. Analiza ficzera (L3 — tldraw, `analytics.tsx`)

**Dlaczego ten przepływ:** bezpośrednio odpowiada strefie ryzyka #1 z mapy (korzeń cykli) i strefie #4 (brak testów `tla/`).

**Feature overview:** `analytics.tsx` (413 linii) to centralna warstwa telemetrii tldraw.com obsługująca trzy zewnętrzne SDK — PostHog (proxy `analytics.tldraw.com/i`), GA4 (`gtag`) i Reo (iframe + postMessage). Input: akcja użytkownika w komponencie wywołuje `trackEvent()` bezpośrednio lub przez hook `useTldrawAppUiEvents()`. Stan zmienia się w `cookieConsent` atomie (localStorage + Clerk DB). Output: HTTP POST do PostHog z `before_send` hook redaktującym PII (`url`, `href`, `pathname`) i doklejającym `ff_*` feature flags. GA4 dostaje wyłącznie `$pageview` i `click-watermark`.

**Technical debt — 3 główne ryzyka:**

1. **Odwrócona zależność (WYSOKI)** — `analytics.tsx:8` zawiera `import { useApp } from '../tla/hooks/useAppState'` (potwierdzone ast-grep). Infrastruktura zna domenę. Korzeń wszystkich 3 cykli; uniemożliwia testy jednostkowe `SignedInAnalytics` bez inicjalizacji pełnego stosu.

2. **PII redaction bez pokrycia (WYSOKI/COMPLIANCE)** — `filterProperties()` (line 75) to jedyna bariera przed wyciekiem `url`/`pathname` do PostHog. Funkcja nie ma żadnego testu. 0 z 24 funkcji analytics.tsx ma test jednostkowy. Jedyny test (`cookie-consent.spec.ts`, 110 linii) weryfikuje wyłącznie UI bannera — nie weryfikuje, czy PostHog/GA4 dostają consent state.

3. **Blast radius 40 plików** — 21 bezpośrednich importerów + 19 pośrednich przez `useTldrawAppUiEvents()`. Sygnatura `trackEvent(name: string, data?: { [key: string]: any })` nie wymusza typowania nazw eventów; zmiana sygnatury = kaskada w 21+ plikach. *(ast-grep: 21 importerów potwierdzone, 12 eksportów potwierdzone)*

---

## 4. Plan refaktoryzacji (L4 — tldraw)

**Co refaktoryzowane:** `apps/dotcom/client/src/utils/analytics.tsx` — 3 PRy.

**Czego świadomie NIE robimy:** nowych testów dla strukturalnych refaktorów; nowego E2E dla pre-init buffering; zmian w `packages/` lub `sync-worker`.

| PR | Cel | Weryfikacja |
|---|---|---|
| **PR 1** | Utwórz `TlaAnalyticsProvider.tsx`, przenieś `SignedInAnalytics` i `SignedOutAnalytics`, usuń `import { useApp }` z `analytics.tsx:8` — przecina 3 cykle | Auto: `yarn typecheck` (0 błędów) + `npx madge --circular src/utils/analytics.tsx` (0 cykli) |
| **PR 2** | Utwórz `tla/types/app-event-types.ts`, zawęź sygnaturę `trackEvent` do `<T extends keyof TLAppUiEventMap>`, scataloguj 10 brakujących eventów, napraw TldrawApp.ts:651 (C5) | Auto: `yarn typecheck` (0 błędów); kaskada przez 21+ importerów |
| **PR 3** | Usuń redundantne bufory ręczne (`eventBufferPosthog`, `eventBufferGA4`) — warunkowo, po potwierdzeniu że SDK kolejkują natywnie | Gate: weryfikacja posthog-js + react-ga4 przed zmianą; smoke test ręczny po |

---

## 5. Domena wg DDD (L5 — corobimy)

**Ubiquitous language — 5 pojęć:**

| Termin | Definicja | Rozjazd model-vs-kod |
|---|---|---|
| **Attraction** | Miejsce lub wydarzenie w Krakowie | — |
| **Category** | Tag z zamkniętego zbioru {family, couples, sport, culture} | PRD: "one or more category tags"; model: `CharField` (single value) — niemożliwe do reprezentacji |
| **Preference Filter** | Opcjonalny filtr kategorii ustawiany przez użytkownika | PRD: "User can **set** a preference filter" (sugeruje persystencję); kod: request-scoped param URL |
| **Save** | Relacja użytkownik–atrakcja oznaczająca wybór | Dobrze egzekwowany (DB unique_together) |
| **Browse-first Pattern** | Przeglądanie bez auth; auth wymagana przy zapisie | Dobrze egzekwowany (@login_required) |

**Niezmiennik #1:** "Atrakcja musi mieć jedną lub więcej kategorii, każda z zamkniętego zbioru {family, couples, sport, culture}" — najsłabiej egzekwowany: `choices=CATEGORY_CHOICES` to walidacja formularza, nie DB constraint; `Attraction.objects.create(category="bogus")` przechodzi bez błędu. Agregat: `Attraction` (root) z `AttractionCategoryTag` (M2M) chronionym przez `CheckConstraint` i metodę fabryczną `Attraction.create(categories=[...])`.

**Anti-Corruption Layer:** `django-filter` przecieka przez 4 warstwy w 14 miejscach (5 plików). Kluczowy leak: `"filter": f` w kontekście widoku (`views.py:30`) — szablon (`list.html:17`) woła `{{ filter.form.as_p }}`, czyli API wewnętrzne biblioteki (`FilterSet.form`) jest widoczne w warstwie UI. Projekt ACL: `ActivePreferenceFilter` (frozen dataclass), port `IPreferenceFilterBuilder`, adapter `DjangoFilterPreferenceFilterAdapter` — jedyny plik mogący importować `AttractionFilter`. Po refaktorze `grep django_filters|AttractionFilter attractions/` zwraca wyłącznie `filters.py` + `adapters.py`. Efekt uboczny: naprawia bug z `lessons.md` (Load More gubił filtry).

---

## 6. Decyzje, które należą do mnie

**tldraw:** AI zidentyfikowało cykl, blast radius i brak typowania, ale decyzja o **kolejności 3 PRów** i **pominięciu testów dla PR1** należy do mnie — szczególnie to drugie jest ryzykiem, bo PII redaction (`filterProperties`) nadal nie będzie pokryte po PR1. Wskazanie **Mitji Bezenška** jako właściciela to podpowiedź AI z historii gita; faktyczny review-gate jest moją decyzją operacyjną.

**corobimy:** AI zaproponowało wielokategorialność (M2M) jako refaktor #1 na podstawie PRD vs. kodu. Moją decyzją jest **kiedy** to zrobić — schemat zmienia się razem z pipeline'em kategoryzacji AI (FR-009, niezaimplementowane). Robienie migracji M2M przed pipeline'em to ryzyko podwójnej zmiany schematu. AI nie może ocenić tego timingu — to decyzja produktowa, nie techniczna.

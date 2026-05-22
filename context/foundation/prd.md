---
project: "corobimy"
version: 1
status: draft
created: 2026-05-22
context_type: greenfield
product_type: web-app
target_scale:
  users: small
  qps: low
  data_volume: small
timeline_budget:
  mvp_weeks: 3
  hard_deadline: null
  after_hours_only: true
---

## Vision & Problem Statement

People planning a visit or a free day in Kraków face a discovery gap: they don't know what attractions are available or which ones suit them. The current approach — browsing TripAdvisor, Google Maps, and local sites — is scattered and produces no personalized signal. The user knows they want to do something, but doesn't know where to start.

This gap is now solvable: AI-driven content analysis makes it cheap to aggregate local Kraków sources and match a person's preferences (family outing, romantic, sport, culture) in real time. This capability wasn't practically available before on-demand text analysis became affordable enough to apply at the individual-request level.

## User & Persona

### Primary persona A: Kraków tourist
A person visiting Kraków (from outside the city or abroad), unfamiliar with what the city offers. They have a day or a few hours and want to know what's worth doing, fast. They reach for this product when they arrive or are planning the trip day-by-day.

### Primary persona B: Kraków local
A Kraków resident looking for something to do on a free evening or weekend. They know the city exists but don't track what's new or available. They reach for this product when they have unstructured free time.

> Note: These two personas have different first flows — locals want "what's new near me?"; tourists want "the highlight reel, fast." Building for both from day one may dilute the MVP. See Open Questions entry 1.

## Success Criteria

### Primary
- ≥ 20% of users who browse the attraction list actually select (save) at least one attraction per session.

### Secondary
- Time from app open to first attraction selection is under 3 minutes (new user, cold start).

### Guardrails
- Attraction data must be current and accurate: no stale listings for closed or non-existent venues. A user who shows up to a closed attraction based on the app's recommendation is a trust-destroying failure.

## User Stories

### US-01: User discovers and saves a Kraków attraction (browse-first)

- **Given** any user (signed in or anonymous) who opens the app
- **When** they browse the attractions feed (optionally setting a preference filter)
- **Then** they see a list of curated Kraków attractions; when they attempt to save one, they are prompted to sign in / register if not yet authenticated; after auth, the attraction is saved

#### Acceptance Criteria
- At least one attraction is visible immediately without requiring sign-in (seed data ensures non-empty initial state)
- Unauthenticated user can browse freely; save action triggers auth prompt
- After completing auth, the save action completes without losing the selected attraction
- A saved attraction is persisted to the user's account

## Functional Requirements

### Authentication
- FR-001: User can create an account with email and password. Priority: must-have
  > Socrates: Browse-first pattern adopted — unauthenticated users can browse; sign-up is prompted only when they attempt to save an attraction. Reduces drop-off before value is demonstrated.
- FR-002: User can sign in to an existing account with email and password. Priority: must-have
  > Socrates: Same browse-first pattern applies. Auth is the gateway to persistence, not to the app.

### Preferences
- FR-003: User can set a preference filter (family / couples / sport / culture). Priority: must-have
  > Socrates: Preference is an optional filter, not a required gate. Default view shows all attractions. Setting a preference narrows the list; not setting one does not block browsing.

### Attractions
- FR-004: User can browse a list of curated Kraków attractions, optionally filtered by preference. Priority: must-have
  > Socrates: The categorization pipeline is the core bet, but is fragile on day 1. Resolved: ship with a hardcoded manual seed of Kraków attractions; automated categorization augments the list over time. Seed ensures app works before the categorization pipeline is stable.
- FR-005: User can select (save) an attraction. Priority: must-have
- FR-006: User can reject (dismiss) an attraction so it does not reappear in their feed. Priority: nice-to-have
  > Socrates: Rejection requires per-user dismissal state — a meaningful data model addition. Demoted to nice-to-have for MVP. Users who browse without rejecting still receive full value via select.
- FR-007: User can search attractions by free-text keyword. Priority: nice-to-have

### History
- FR-008: User can view their history of previously selected attractions. Priority: nice-to-have
  > Socrates: History view is most valuable for returning/local users; tourists with short trips gain little from it. Demoted to nice-to-have. Saved attractions are still persisted — the history screen is a v2 feature.

### Content
- FR-009: Operator can manually trigger a refresh of Kraków attraction listings from local websites. Priority: must-have
  > Socrates: Automated scraping is fragile (site structure changes, bot blocking). For MVP, a manual operator trigger is safer. Automated periodic refresh is a v2 capability.

## Non-Functional Requirements

- The attraction list is visible to the user within 2 seconds of opening the feed or changing a filter, under typical mobile network conditions.
- A user's saved attractions and stated preferences are used only to serve that user's own feed; they are never shared with third parties or used for advertising.

## Business Logic

The app assigns each Kraków attraction a category tag (family / couples / sport / culture) and shows only those matching the user's active preference filter.

Kraków attractions are sourced from local websites and assigned one or more category tags based on their content. When a user sets a preference filter, they see only attractions tagged with their chosen category. When no filter is set, all available tagged attractions are shown. The categorization is the sole decision the product makes for the user — it does not rank, score, or further personalize beyond the user's explicit category choice.

The attraction corpus is populated and refreshed through an operator-initiated process. The app reads from the current corpus; it does not schedule or trigger refreshes autonomously.

## Access Control

Authentication: email + password. Browse-first pattern: unauthenticated users can browse the attraction feed freely; sign-up/sign-in is prompted only when they attempt to save an attraction.

Role model: flat — one role (authenticated user). All logged-in users have identical access.

No admin role in MVP — content is operator-managed via manual trigger.

Unauthenticated access: read-only (browse + filter). Saving requires authentication.

## Non-Goals

- **No native mobile app for MVP** — web-only. Mobile apps require separate deployment, app store approval, and platform-specific builds. This is a deliberate v2 decision.
- **No behavioral recommendation algorithm** — the app uses explicit preference filters only (family / couples / sport / culture). No recommendations derived from usage history. This keeps the domain rule tractable and the categorization pipeline simple.
- **No social / sharing features** — saved attractions are private to each user. No shared lists, friend activity, or collaborative planning.
- **No multi-city support** — Kraków only. Expanding to other cities requires separate content pipelines. Deferred until product-market fit is validated in Kraków.
- **No automated content refresh in MVP** — operator manually triggers the data refresh. Automated scheduling is a v2 capability.

## Open Questions

1. **Dual-persona tension** — Tourist vs. local first flows differ significantly. Which persona should the MVP serve first? Owner: user. Block: no (both personas allowed, but MVP focus matters for day-1 UX decisions).

# Login/Logout Button — Plan Brief

> Full plan: `context/changes/login-logout-button/plan.md`

## What & Why

Add a slim persistent header to every page showing the current auth state. Users currently have no visual indication of whether they are logged in, and no quick path to login or logout without knowing the direct URL. This surfaces the existing S-02 auth infrastructure as a first-class UI element.

## Starting Point

`base.html` is a 14-line bare shell — no header, no nav, no auth display. Django's auth context processor is already enabled so `{{ user }}` is available in all templates for free. Login, logout, and register URLs are fully wired from S-02.

## Desired End State

Every page has a slim top bar (app name left, auth controls right). Anonymous users see a "Login" link with `?next=` pre-filled to their current URL. Authenticated users see "Hi, [username]" and a Logout button.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Placement | `base.html` (all pages) | Consistent auth visibility everywhere; one change covers all templates | Plan |
| Logged-in display | Username + Logout button | Confirms identity — especially useful for shared devices | Plan |
| Anonymous display | Login link only | Register is discoverable from the login page; keeps the header minimal | Plan |
| Style | Slim Tailwind bar | Matches existing `max-w-5xl mx-auto px-4` layout; no new assets | Plan |
| Logout method | POST form | Django 6.0.5 `LogoutView` rejects GET — plain `<a>` returns 405 | Plan |

## Scope

**In scope:** `base.html` header with conditional auth block

**Out of scope:** Register link in header, sticky/fixed positioning, dropdown/avatar menu, new views or URL changes, any template other than `base.html`

## Architecture / Approach

Single-file template change. Insert `<header>` in `base.html` before `{% block content %}`. Use `{{ user.is_authenticated }}` and `{{ user.username }}` from Django's auth context processor. Logout wrapped in `<form method="post">{% csrf_token %}</form>` to satisfy POST-only requirement.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Header in base.html | Slim nav bar with conditional auth on every page | POST-only logout must use a form, not an `<a>` tag |

**Prerequisites:** S-02 done (auth views, URLs, and session handling are in place)
**Estimated effort:** ~1 session, single file

## Open Risks & Assumptions

- `django.template.context_processors.request` must be in `TEMPLATES` settings for `{{ request.path }}` to be available in templates; assumed present (standard Django default)
- `LOGOUT_REDIRECT_URL` not set — after logout, Django shows `registration/logged_out.html` by default; no change needed unless redirect to home is desired (out of scope)

## Success Criteria (Summary)

- Anonymous users see a Login link in the header on every page
- Authenticated users see their username and a working Logout button
- No layout regressions on login, register, or main attractions pages

# Login/Logout Button Implementation Plan

## Overview

Add a slim persistent header to `base.html` so every page shows auth state. Anonymous users see a "Login" link; authenticated users see "Hi, [username]" plus a Logout button. The auth infrastructure (views, URLs, templates) is fully in place from S-02 — this change is purely presentational.

## Current State Analysis

`base.html` is a 14-line shell with no header or navigation. All custom templates extend it, so no page currently displays auth state. Django's auth context processor is configured, making `{{ user }}` available in every template without extra view work. Auth URL names (`login`, `logout`) are registered via `django.contrib.auth.urls` at `corobimy/urls.py:25`.

## Desired End State

Every page has a slim top bar with the app name on the left and auth controls on the right. Anonymous visitors see a "Login" link (with `?next=` pre-filled to the current URL so they return after login). Logged-in users see "Hi, [username]" and a Logout button that POSTs to Django's `LogoutView`.

### Key Discoveries

- `templates/base.html:10` — CSRF token is set globally via `hx-headers` for HTMX only; a standard `<form method="post">` still needs `{% csrf_token %}` inline
- `corobimy/urls.py:25` — URL name `logout` comes from `django.contrib.auth.urls`; `LogoutView` in Django 6.0.5 accepts POST only — a plain `<a href="...logout...">` returns 405
- Existing pages use `max-w-5xl mx-auto px-4` — the header should match this max-width for visual consistency

## What We're NOT Doing

- No "Register" link in the header (user chose Login-only for anonymous state; Register is discoverable from the login page)
- No sticky/fixed positioning
- No dropdown, avatar, or profile menu
- No changes to auth views, URL config, or existing templates other than `base.html`
- No new views, models, or migrations

## Implementation Approach

Single-file template change to `base.html`. Insert a `<header>` element between the `<body>` opening and `{% block content %}`. Use `{{ user.is_authenticated }}` and `{{ user.username }}` (available via context processor). Wrap the logout trigger in a POST form to satisfy Django 6's POST-only logout requirement.

## Critical Implementation Details

**POST-only logout**: Django 6.0.5's `LogoutView` rejects GET requests. The logout trigger must be a `<button type="submit">` inside `<form method="post" action="{% url 'logout' %}">{% csrf_token %}</form>`. A plain `<a href="{% url 'logout' %}">` produces a 405 Method Not Allowed.

---

## Phase 1: Add persistent header to base.html

### Overview

Insert a slim `<header>` element into `base.html` that renders on every page. App name on the left, conditional auth controls on the right.

### Changes Required

#### 1. base.html — header with conditional auth controls

**File**: `templates/base.html`

**Intent**: Add a `<header>` between the `<body>` tag and `{% block content %}` that shows the app name on the left and auth controls on the right. For anonymous users: a "Login" link with `?next={{ request.path }}`. For authenticated users: "Hi, {{ user.username }}" text and a POST form containing a Logout submit button.

**Contract**: The header uses Tailwind utilities. Outer wrapper: `class="bg-white border-b border-gray-200"`. Inner flex row: `max-w-5xl mx-auto px-4 py-3 flex items-center justify-between`. Left: app name as `<span>` or `<a href="{% url 'attraction-list' %}">`. Right: `{% if user.is_authenticated %}` block with username text and logout form; `{% else %}` block with Login link. The logout form needs `{% csrf_token %}` inline.

### Success Criteria

#### Automated Verification

- Django system check passes: `python manage.py check`
- Linting passes (project lint command)

#### Manual Verification

- Anonymous user visits any page → slim header visible with "Login" link in top-right
- Login link URL includes `?next=<current-path>`
- After login, header shows "Hi, [username]" and a "Logout" button
- Clicking Logout POSTs to `accounts/logout/` and logs the user out
- Header renders consistently on the login page, register page, and main attractions page — no layout regressions

**Implementation Note**: After automated verification passes, pause for manual testing of the full anonymous → login → logout flow before marking this phase complete.

---

## Testing Strategy

### Manual Testing Steps

1. Visit main page as anonymous → confirm header shows "Login" link with `?next=/` or `?next=/attractions/` (current path)
2. Click "Login" → complete login → confirm redirect back to the original page
3. Confirm header now shows "Hi, [username]" and "Logout" button
4. Click "Logout" → confirm POST to `accounts/logout/`, user session cleared
5. Navigate to login and register pages → confirm header renders there without breaking those forms

## References

- Auth URL names registered at: `corobimy/urls.py:25`
- Logout POST-only requirement: Django 5.0+ change, still applies in 6.0.5
- Login URL name: `login` | Logout URL name: `logout` (from `django.contrib.auth.urls`)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Add persistent header to base.html

#### Automated

- [x] 1.1 Django system check passes (`python manage.py check`) — 6e7ac8a
- [x] 1.2 Lint passes — 6e7ac8a

#### Manual

- [x] 1.3 Anonymous user sees Login link in header on any page — 6e7ac8a
- [x] 1.4 Login link includes `?next=` pre-filled to current URL — 6e7ac8a
- [x] 1.5 Authenticated user sees "Hi, [username]" and Logout button — 6e7ac8a
- [x] 1.6 Logout POSTs to `accounts/logout/` and logs user out — 6e7ac8a
- [x] 1.7 Header renders on login and register pages without regression — 6e7ac8a

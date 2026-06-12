---
date: 2026-06-12T00:00:00+02:00
researcher: Przemek
git_commit: 4677eba0829254fa6854b45d36c1210eb4e88e77
branch: main
repository: corobimy
topic: "S-02 critical path: save persistence across auth redirect, server-side auth gate, user-scope isolation"
tags: [research, codebase, attractions, accounts, save, auth, user-scope]
status: complete
last_updated: 2026-06-12
last_updated_by: Przemek
---

# Research: S-02 Critical Path (Phase 1 Test Rollout)

**Date**: 2026-06-12  
**Researcher**: Przemek  
**Git Commit**: 4677eba0829254fa6854b45d36c1210eb4e88e77  
**Branch**: main  
**Repository**: corobimy

## Research Question

Ground the three Phase 1 risks (`test-plan.md §3 Phase 1`) in live code so that plan.md can write precise, runnable Django integration tests:

- **Risk #1** — Save lost at auth redirect (anonymous save → register/login → save absent)
- **Risk #2** — Save endpoint accepts unauthenticated POST server-side
- **Risk #3** — Saved attractions leaked across users

## Summary

The save mechanism uses **Django's built-in `?next=` redirect chain** rather than explicit session storage. The login path works correctly end-to-end; the **register path is broken** — `accounts/views.py:13` always redirects to `LOGIN_REDIRECT_URL = '/'` and never reads `?next=`, so any anonymous user who registers (instead of logging in) loses their pending save. Server-side auth enforcement is real (`@login_required` on the view), and user-scope filtering is correct. Zero tests currently exist for the save endpoint, auth redirect, or user-scope isolation.

---

## Detailed Findings

### Risk #1 — Save persistence across auth redirect

**How the mechanism works:**

1. Anonymous user POSTs to `/attractions/<pk>/save/`
2. `@login_required` intercepts → 302 to `/accounts/login/?next=/attractions/<pk>/save/`
3. The attraction `pk` is carried **only** in the `next` URL param — no session storage, no pre-auth buffer
4. After auth, the redirect target depends on which auth path the user took:

**Login path (Django's built-in auth view):**  
`/accounts/login/` reads the `next` param from POST form field (`<input type="hidden" name="next" value="{{ next }}">`) and redirects to `/attractions/<pk>/save/` → view runs again → `get_or_create` creates the row → redirects to `attraction-list` ✓

**Register path (custom `accounts/views.py`):**  
`register()` calls `redirect(settings.LOGIN_REDIRECT_URL)` which resolves to `redirect('/')`. It does **not** read `?next=` from `request.GET` or `request.POST`. The attraction pk is lost. ✗

**The bug — `accounts/views.py:13`:**

```python
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            django_auth.login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)   # ← always '/', ignores ?next=
```

[`accounts/views.py:7–16`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/accounts/views.py#L7-L16)

**The save view (works after login, never reached after register):**

```python
@login_required
def save_attraction(request, pk):
    # Accepts GET and POST: @login_required redirects anonymous users to login with ?next=<url>,
    # then Django sends a GET back here after auth — get_or_create makes both methods safe.
    attraction = get_object_or_404(Attraction, pk=pk)
    UserSavedAttraction.objects.get_or_create(user=request.user, attraction=attraction)
    return redirect('attraction-list')
```

[`attractions/views.py:42–48`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/views.py#L42-L48)

**Key settings:**  
[`corobimy/settings.py:140`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/corobimy/settings.py#L140) — `LOGIN_REDIRECT_URL = '/'`  
[`corobimy/urls.py:24`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/corobimy/urls.py#L24) — `path('accounts/', include('django.contrib.auth.urls'))` — Django's built-in login view lives here

**Test implications for Risk #1:**

The test plan says the test "must confirm the save, not just the logged-in state." Two sub-cases must be written:

| Sub-case | Expected result today | Test approach |
|---|---|---|
| Anonymous → login → save | PASS — save row created | `client.post(save_url)` → follow to `/accounts/login/` → `client.post('/accounts/login/', {..., 'next': save_url}, follow=True)` → assert `UserSavedAttraction.objects.filter(user=user, attraction=attraction).exists()` |
| Anonymous → register → save | **FAIL** — save row NOT created (exposes the bug) | `client.post(save_url)` → follow → `client.post('/accounts/register/', {...}, follow=True)` → assert `UserSavedAttraction.objects.filter(user=user, attraction=attraction).exists()` — this will fail until the register view is fixed |

---

### Risk #2 — Server-side auth enforcement

**Verdict: properly enforced.** `@login_required` is on the view function, not just the UI.

[`attractions/views.py:42`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/views.py#L42)

- Anonymous POST → 302 to `/accounts/login/?next=/attractions/<pk>/save/`
- Zero database rows created (the view body never executes)
- The UI shows the Save form to anonymous users (because `saved_pks = set()` for unauthenticated users), so the save button is visible but the endpoint enforces auth independently

[`attractions/views.py:24–25`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/views.py#L24-L25) — `saved_pks = set()` for unauthenticated users, meaning every attraction shows the Save button for anonymous visitors

**Test implications for Risk #2:**

```python
response = self.client.post(reverse('attraction-save', args=[attraction.pk]))
self.assertRedirects(response, '/accounts/login/?next=/attractions/1/save/')
self.assertEqual(UserSavedAttraction.objects.count(), 0)
```

---

### Risk #3 — User-scope isolation

**Verdict: correctly filtered at query level.**

**The queryset in `attraction_list`:**

```python
if request.user.is_authenticated:
    page_pks = [a.pk for a in page_attractions]
    saved_pks = set(
        UserSavedAttraction.objects.filter(user=request.user, attraction_id__in=page_pks)
        .values_list('attraction_id', flat=True)
    )
else:
    saved_pks = set()
```

[`attractions/views.py:18–25`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/views.py#L18-L25)

**The save operation:**  
[`attractions/views.py:47`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/views.py#L47) — `get_or_create(user=request.user, attraction=attraction)` — user-scoped write

**Model-level constraint:**

```python
class UserSavedAttraction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_attractions')
    attraction = models.ForeignKey(Attraction, on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'attraction')]
        ordering = ['-saved_at']
```

[`attractions/models.py:25–35`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/models.py#L25-L35)

No dedicated "my saved list" view exists — the only surface is the `attraction_list` view, which correctly filters `saved_pks` per-user. No REST API or JSON endpoint exists that could expose cross-user data.

**Test implications for Risk #3:**

Create two users. Save an attraction as User A. Assert User B's `saved_pks` (from the view context) does not contain that attraction pk.

---

## Code References

| File | Lines | Description |
|---|---|---|
| [`attractions/views.py:42–48`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/views.py#L42-L48) | 42–48 | `save_attraction` view — `@login_required` + `get_or_create` |
| [`attractions/views.py:18–25`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/views.py#L18-L25) | 18–25 | `saved_pks` queryset — user-scoped filter |
| [`attractions/models.py:25–35`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/models.py#L25-L35) | 25–35 | `UserSavedAttraction` model — `unique_together`, FKs |
| [`attractions/urls.py:6`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/urls.py#L6) | 6 | `path('attractions/<int:pk>/save/', ...)` named `attraction-save` |
| [`accounts/views.py:7–16`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/accounts/views.py#L7-L16) | 7–16 | `register()` view — the broken post-register redirect |
| [`accounts/views.py:13`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/accounts/views.py#L13) | 13 | `return redirect(settings.LOGIN_REDIRECT_URL)` — loses `?next=` |
| [`corobimy/settings.py:140`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/corobimy/settings.py#L140) | 140 | `LOGIN_REDIRECT_URL = '/'` |
| [`corobimy/urls.py:24`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/corobimy/urls.py#L24) | 24 | Django's built-in auth URLs (login view that reads `?next=`) |
| [`attractions/tests.py:1–111`](https://github.com/bozowski/corobimy/blob/4677eba0829254fa6854b45d36c1210eb4e88e77/attractions/tests.py#L1-L111) | 1–111 | All existing tests — none cover save, auth, or user-scope |

---

## Architecture Insights

**The `?next=` mechanism is the entire pre-auth buffer.** There is no explicit session key, no `pending_save` field, no middleware. The attraction pk lives in the URL. This is elegant but means it only works when the auth flow reads and honours `?next=` — which Django's built-in login view does and the custom register view does not.

**`get_or_create` serves as idempotency and GET-safety.** The view accepts both GET and POST, because Django redirects back with a GET after login. The comment in the view documents this intentional design. `unique_together` at the DB level is the second idempotency layer.

**No REST API.** The entire app is server-rendered HTML + HTMX. There is no DRF serializer, no `JsonResponse` for saves. The only save surface is `attraction-save` and the only read surface is `saved_pks` in the `attraction_list` context.

**Test runner:** `uv run python manage.py test` — Django's built-in TestCase, no pytest. SQLite in test mode. HTMX requests simulated with `HTTP_HX_REQUEST='true'` header.

---

## Historical Context

No prior research artifacts exist for this change folder or related archived changes.

---

## Open Questions

1. **Should the register bug be fixed before or alongside writing the test?** The test for Risk #1 (register path) will fail until `accounts/views.py:13` reads and forwards `?next=`. The plan should decide: (a) write the failing test first as a regression anchor, then fix; or (b) fix first, then write the test as a passing verification. Option (a) is the stricter TDD approach and matches the test-plan's intent of surfacing the risk.

2. **Does the login template link to register with `?next=` preserved?** Not confirmed. If the "Register" link on the login page does not include `?next=`, the register page never receives it in the first place. Worth checking `templates/registration/login.html` when authoring the test.

3. **Is `LOGIN_URL` explicitly set in settings?** Not found in the review. Django defaults to `/accounts/login/`. This matters for the expected redirect URL in the Risk #2 test assertion.

---
bootstrapped_at: 2026-05-24T23:01:00Z
starter_id: django
starter_name: Django
project_name: corobimy
language_family: python
package_manager: uv
cwd_strategy: native-cwd
bootstrapper_confidence: verified
phase_3_status: ok
audit_command: "pip-audit --format json"
---

## Hand-off

Verbatim frontmatter from `context/foundation/tech-stack.md`:

```yaml
starter_id: django
package_manager: uv
project_name: corobimy
hints:
  language_family: python
  team_size: solo
  deployment_target: fly
  ci_provider: github-actions
  ci_default_flow: auto-deploy-on-merge
  bootstrapper_confidence: verified
  path_taken: standard
  quality_override: false
  self_check_answers: null
  has_auth: true
  has_payments: false
  has_realtime: false
  has_ai: false
  has_background_jobs: false
```

### Why this stack

A solo developer shipping a 3-week after-hours MVP for a Kraków attraction discovery web app
needs the shortest path to a working full-stack product with auth and a database. Django is
the vetted default for `(web-app, python)`: it ships auth, ORM, admin, and migrations out of
the box, matching all three load-bearing corobimy requirements — browse-first email/password
auth (FR-001/002), operator-managed attraction seed data (FR-004/009), and a
PostgreSQL-backed corpus. The small user scale and tight timeline favor Django's
batteries-included defaults over assembling a separate auth layer or frontend. Fly.io is the
deployment default for the Django card; GitHub Actions with auto-deploy-on-merge keeps the
solo contributor loop tight. Bootstrapper confidence is verified — end-to-end scaffolding has
been tested on this stack.

## Pre-scaffold verification

| Signal      | Value                                         | Severity | Notes                                                                                   |
| ----------- | --------------------------------------------- | -------- | --------------------------------------------------------------------------------------- |
| npm package | not run                                       | n/a      | python language family — no npm check                                                   |
| GitHub repo | not run                                       | n/a      | `docs_url` (https://docs.djangoproject.com) is not a GitHub URL; no recency signal     |

## Scaffold log

**Resolved invocation**: `django-admin startproject corobimy .`

> v1 deviation: the native-cwd substitution rule (`{name}=.`) was not applied verbatim. Django's
> `cmd_template` is `django-admin startproject {name} .` where `{name}` is the project name (must be
> a valid Python identifier) and the trailing `.` is the target directory. Substituting `{name}=.`
> would produce `django-admin startproject . .`, which Django rejects. `project_name` (`corobimy`)
> was used as `{name}` instead. Logged here as an audit-trail note for the v2 registry update.

**Additional pre step (registry card `pre` field)**: `pip install django`
> `uv` (the hand-off's `package_manager`) was not found on system PATH. A Python venv was created
> with `python -m venv .venv` and Django was installed via the venv's pip. `uv` will need to be
> installed separately for ongoing dependency management.

**Strategy**: native-cwd (scaffold directly into the current directory)

**Exit code**: 0

**Pre-flight files-to-touch**: `manage.py`, `corobimy/__init__.py`, `corobimy/asgi.py`, `corobimy/settings.py`, `corobimy/urls.py`, `corobimy/wsgi.py`

**Files written by CLI**: 6
- `manage.py`
- `corobimy/__init__.py`
- `corobimy/asgi.py`
- `corobimy/settings.py`
- `corobimy/urls.py`
- `corobimy/wsgi.py`

**Pre-existing files preserved**: `.agents/`, `.claude/`, `.git/`, `CLAUDE.md`, `context/`, `idea-notes.md`, `LICENSE`, `README.md`, `skills-lock.json`

## Post-scaffold audit

**Tool**: `pip-audit --format json`

**Summary**: 0 CRITICAL, 0 HIGH, 3 MODERATE, 0 LOW

**Direct vs transitive**: not distinguished by pip-audit

> Django 6.0.5 and all other project dependencies: 0 vulnerabilities. All 3 findings are in
> `pip` v25.3 (the venv's package manager toolchain), not in project code or Django itself.

#### MODERATE findings

| Package | Version | CVE          | Fix version | Description                                                                                                                                                      |
| ------- | ------- | ------------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| pip     | 25.3    | CVE-2026-1703 | 26.0        | Path traversal when extracting a maliciously crafted wheel archive; limited to prefixes of the installation directory.                                            |
| pip     | 25.3    | CVE-2026-3219 | 26.1        | pip handles concatenated tar+ZIP files as ZIP regardless of filename; could result in installing incorrect files.                                                 |
| pip     | 25.3    | CVE-2026-6357 | 26.1        | pip ran self-update check after installing wheels, importing well-known module names from newly-installed packages; patched to run self-update before wheel install. |

**Recommended action**: upgrade the venv's pip with `.venv/Scripts/python -m pip install --upgrade pip`.

## Hints recorded but not acted on

| Hint                    | Value                  |
| ----------------------- | ---------------------- |
| bootstrapper_confidence | verified               |
| quality_override        | false                  |
| path_taken              | standard               |
| self_check_answers      | null                   |
| team_size               | solo                   |
| deployment_target       | fly                    |
| ci_provider             | github-actions         |
| ci_default_flow         | auto-deploy-on-merge   |
| has_auth                | true                   |
| has_payments            | false                  |
| has_realtime            | false                  |
| has_ai                  | false                  |
| has_background_jobs     | false                  |

These values were read and preserved in this log. Bootstrapper v1 takes no automated action on them. A future M1L4 skill ("Memory Architecture") will act on deployment_target, ci_provider, ci_default_flow, and the has_* feature flags to scaffold agent context (CLAUDE.md, AGENTS.md, CI workflows, etc.).

## Next steps

Next: a future skill will set up agent context (CLAUDE.md, AGENTS.md). For now, your project is scaffolded and verified — happy hacking.

Useful manual steps in the meantime:
- Install `uv` (https://docs.astral.sh/uv/) for dependency management as chosen in the hand-off.
- Upgrade the venv's pip to clear the 3 MODERATE findings: `.venv\Scripts\python -m pip install --upgrade pip`
- Run `python manage.py migrate` to apply Django's initial migrations.
- Run `python manage.py createsuperuser` to create an admin account.
- Review `.venv/` — it is in cwd and should be added to `.gitignore` (Django's startproject does not add a `.gitignore` automatically).
- Review any `.scaffold` siblings the conflict policy created and decide which version to keep (none were created on this run — no conflicts detected).
- Address audit findings per your project's risk tolerance — the full breakdown is above.

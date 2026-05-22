---
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
---

## Why this stack

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

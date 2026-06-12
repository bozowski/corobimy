# Lessons Learned

> Append-only register of recurring rules and patterns. Re-read at start by /10x-frame, /10x-research, /10x-plan, /10x-plan-review, /10x-implement, /10x-impl-review.

## HTMX pagination must forward all active filter params

**Context:** attractions/templates/attractions/partials/filter_results.html — Load More button

**Problem:** The HTMX Load More button manually threads individual filter query params (e.g. `?category=`) into the URL. When a new filter field is added to AttractionFilter, it is silently dropped on pagination until someone remembers to add it to every paginate button.

**Rule:** When building HTMX pagination URLs, serialise the full filter form data (e.g. `f.form.data`) rather than listing individual params. This ensures all current and future filter fields are preserved automatically.

**Applies to:** Any template that renders a Load More or paginate button alongside a django-filters filter form.

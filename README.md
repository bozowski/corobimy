# corobimy

A Kraków attraction discovery web app. Tourists and locals browse curated attractions filtered by preference (family / couples / sport / culture), then save the ones they want to visit. Browsing is open to anyone; saving requires an account.

## Tech stack

- Python 3.13+ / Django 6
- SQLite (dev) / PostgreSQL (production)
- [uv](https://docs.astral.sh/uv/) for dependency management
- WhiteNoise for static files, Gunicorn for production serving
- Deployed on Railway

## Local setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

### Steps

```bash
# 1. Clone the repo
git clone <repo-url>
cd corobimy

# 2. Install dependencies
uv sync

# 3. Create a .env file
cp .env.example .env   # or create manually — see below

# 4. Apply migrations
uv run python manage.py migrate

# 5. Load seed attractions
uv run python manage.py loaddata attractions/fixtures/*.json

# 6. Start the dev server
uv run python manage.py runserver
```

Open http://127.0.0.1:8000.

### Environment variables

Create a `.env` file at the project root:

```env
SECRET_KEY=django-insecure-dev-only-do-not-use-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

For production, also set:

```env
SECRET_KEY=<strong-random-key>
DEBUG=False
ALLOWED_HOSTS=<your-domain>
DATABASE_URL=postgres://<user>:<password>@<host>/<db>
```

## Running tests

```bash
uv run pytest
```

## Code quality

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy .
```

Pre-commit hooks (via Lefthook) run lint and format automatically on staged files:

```bash
uv run lefthook install
```

## Production deployment

The app is deployed on [Railway](https://railway.app). The deploy command (defined in `railway.toml`):

```bash
python manage.py collectstatic --no-input && \
python manage.py migrate && \
gunicorn corobimy.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --access-logfile -
```

Health check endpoint: `GET /health/`

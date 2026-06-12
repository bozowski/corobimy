import os


def pytest_configure(config):
    os.environ.setdefault("SECRET_KEY", "django-insecure-dev-only-do-not-use-in-production")
    os.environ.setdefault("DEBUG", "True")

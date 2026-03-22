import os


# Must be set before importing the main settings module so that settings.py
# does not raise "SECRET_KEY must be set".
os.environ.setdefault("SECRET_KEY", "insecure-test-key-only-not-for-production")
os.environ.setdefault("ENV", "dev")

from split_expense_system.settings import *  # noqa: F401, F403, E402


# Database SQLite in-memory

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Channels – use the in-memory layer
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


# Cache – use a simple local-memory cache (no R`edis required)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Email – suppress all outgoing mail in tests
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"


# Password hashing – use the fastest hasher so tests run quickly
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Token lifetimes – short values for fast expiry tests

ACCESS_TOKEN_LIFETIME = 15  # minutes
REFRESH_TOKEN_LIFETIME = 60  # minutes
REFRESH_TOKEN_REMAIN = 1  # seconds
OTP_LIFETIME = 2  # minutes

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Use env var for DEBUG; default False in prod
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ["1", "true", "yes"]

# Allow your domains and Render preview URLs
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# Static files (collectstatic will place files here)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # must exist or be creatable

# Optional but recommended if serving static from app (no CDN/proxy)
# pip install whitenoise
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # add directly after SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Enable gzip/brotli static file serving by WhiteNoise (optional)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

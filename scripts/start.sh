#!/usr/bin/env bash
set -euo pipefail

echo "[start] Python: $(python -V)"
echo "[start] PWD: $(pwd)"
echo "[start] PORT: ${PORT:-<unset>}"

# Quick sanity check: can we import the WSGI app?
python - <<'PY'
import os, importlib, traceback
os.environ.setdefault("DJANGO_SETTINGS_MODULE","soilmoisture_site.settings")
try:
    import soilmoisture_site.wsgi as wsgi
    print("[start] WSGI import OK:", wsgi.application)
except Exception as e:
    print("[start] WSGI import FAILED")
    traceback.print_exc()
    raise
PY

# Don't run heavy work here; keep it fast so the port opens quickly.
# Migrations/static should run in build time.

# Start Gunicorn and bind to the platform PORT
exec gunicorn soilmoisture_site.wsgi:application \
  --bind 0.0.0.0:${PORT} \
  --workers "${WEB_CONCURRENCY:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --log-file -

#!/usr/bin/env bash
set -euo pipefail

# Build step on Render: installs deps and collects static assets

# Detect Python
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "python3 not found. Set PYTHON_BIN to your Python executable." >&2
  exit 1
fi

# Upgrade pip tooling
"${PYTHON_BIN}" -m pip install --upgrade pip setuptools wheel

# Install Python dependencies
pip install -r requirements.txt

# Ensure STATIC_ROOT exists (must match settings.STATIC_ROOT)
mkdir -p staticfiles

# Collect static files (requires STATIC_ROOT set in Django settings)
python manage.py collectstatic --noinput

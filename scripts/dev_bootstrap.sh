#!/usr/bin/env bash
set -euo pipefail

# This script bootstraps and runs the Django app.
# It can be executed from any directory; it will cd to the project root (where manage.py lives).

# Resolve script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Detect Python
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "python3 not found. Set PYTHON_BIN to your Python executable." >&2
  exit 1
fi

# Create venv if missing
if [ ! -d ".venv" ]; then
  "${PYTHON_BIN}" -m venv .venv
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

# Upgrade packaging tools
python -m pip install --upgrade pip setuptools wheel

# Install requirements
pip install -r requirements.txt

# Make and apply migrations
python manage.py makemigrations core
python manage.py migrate


HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
python manage.py runserver "${HOST}:${PORT}"

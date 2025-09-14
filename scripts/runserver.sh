#!/usr/bin/env bash
set -euo pipefail

# Starts the Django development server
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

source .venv/bin/activate

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
python manage.py runserver "${HOST}:${PORT}"

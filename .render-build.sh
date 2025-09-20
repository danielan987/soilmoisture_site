#!/usr/bin/env bash
set -euo pipefail
python -V
pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --noinput || true

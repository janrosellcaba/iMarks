#!/usr/bin/env bash
# Deploy iMarks on Ubuntu/Debian: git pull, venv, migrate, static files, restart Gunicorn.
set -euo pipefail

# Run from the project root even if invoked from another directory.
cd "$(dirname "$0")"

echo "==> Pulling latest code"
git pull

echo "==> Activating virtualenv"
# shellcheck source=/dev/null
source venv/bin/activate

echo "==> Installing dependencies"
pip install -r requirements.txt

echo "==> Applying database migrations"
python manage.py migrate

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Restarting iMarks (Gunicorn)"
sudo systemctl restart iMarks

echo "==> Deploy complete"
systemctl is-active --quiet iMarks && echo "    iMarks is active"

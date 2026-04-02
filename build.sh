#!/usr/bin/env bash
set -o errexit

# ── Frontend ──
cd frontend
npm install
npm run build
cd ..

# ── Backend ──
cd backend
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

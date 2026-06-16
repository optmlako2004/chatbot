#!/bin/bash
# Lance le backend FastAPI (utilise le venv dédié backend/.venv)
set -e
cd "$(dirname "$0")/backend"

VENV=".venv"
PY="$VENV/bin/python3"

# Crée le venv dédié s'il n'existe pas encore, puis installe les dépendances.
if [ ! -x "$PY" ]; then
    echo "venv absent, création de $VENV ..."
    python3 -m venv "$VENV"
    "$PY" -m pip install --upgrade pip -q
    echo "Installation des dépendances (requirements.txt) ..."
    "$PY" -m pip install -r requirements.txt
fi

if [ ! -f voyage.db ]; then
    echo "BDD manquante, lancement du seed..."
    "$PY" seed.py
fi

echo "Backend disponible sur http://localhost:8000"
echo "Frontend : ouvrir frontend/index.html dans le navigateur"
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

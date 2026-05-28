#!/bin/bash
# Lance le backend FastAPI
cd "$(dirname "$0")/backend"

if [ ! -f voyage.db ]; then
    echo "BDD manquante, lancement du seed..."
    python3 seed.py
fi

echo "Backend disponible sur http://localhost:8000"
echo "Frontend : ouvrir frontend/index.html dans le navigateur"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

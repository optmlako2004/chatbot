"""
Configuration pytest commune.

Stratégie :
- BDD SQLite **en mémoire** (jamais sur disque) → tests isolés et rapides
- L'agent LangGraph est mocké → on ne touche pas à Ollama / FAISS dans les
  tests unitaires (sinon ils mettent 30s+ et plantent si Ollama est éteint).
- Une fixture `client` pré-configure FastAPI avec ces overrides.
"""

import os
import sys
from pathlib import Path

# BDD SQLite fichier temporaire (reset entre chaque test). On évite :memory:
# car SQLite crée une nouvelle base par connexion → les tables n'existent pas
# entre threads/requests sans StaticPool, ce qui complexifie le setup.
import tempfile

_DB_PATH = Path(tempfile.gettempdir()) / "sae2_test.db"
os.environ["DB_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret"

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def fake_chat():
    """Mock l'agent LangGraph pour éviter de toucher à Ollama/FAISS dans les tests."""
    def _fake(agent, message, thread_id):
        if "taux" in message.lower() or "2026" in message:
            return {"answer": f"Taux mocké pour: {message}", "tools_used": ["web_search"]}
        return {"answer": f"Définition mockée pour: {message}", "tools_used": ["rag_finance"]}
    return _fake


@pytest.fixture
def client(fake_chat):
    """Client de test FastAPI avec agent mocké et BDD fraîche en mémoire."""
    # Patch build_agent (sinon il essaie de charger Ollama au démarrage de l'API)
    with patch("chatbot.build_agent", return_value="MOCK_AGENT"), \
         patch("chatbot.chat_with_trace", side_effect=fake_chat):
        # Imports DIFFÉRÉS pour que les patchs prennent effet
        import importlib

        import api
        importlib.reload(api)

        # Reset BDD à chaque test (la BDD :memory: est partagée par fixture)
        from db import reset_db
        reset_db()

        with TestClient(api.app) as c:
            yield c


@pytest.fixture
def alice_token(client):
    """Crée un user 'alice' et renvoie son token JWT."""
    r = client.post("/auth/signup", json={
        "email": "alice@test.com",
        "password": "alice123",
        "name": "Alice",
    })
    assert r.status_code == 201, r.text
    return r.json()["token"]


@pytest.fixture
def alice_headers(alice_token):
    return {"Authorization": f"Bearer {alice_token}"}


@pytest.fixture
def anon_headers():
    """Headers pour un user anonyme."""
    return {"X-Anonymous-Id": "test-anon-uuid-1234"}

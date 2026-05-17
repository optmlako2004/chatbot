"""Tests sessions : CRUD, end, feedback, isolation entre users."""


def test_create_and_list_session(client, alice_headers):
    r = client.post("/sessions", json={"title": "Test conv"}, headers=alice_headers)
    assert r.status_code == 201
    sid = r.json()["id"]

    r = client.get("/sessions", headers=alice_headers)
    assert r.status_code == 200
    sessions = r.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == sid
    assert sessions[0]["status"] == "active"


def test_list_sessions_empty_for_new_user(client, alice_headers):
    r = client.get("/sessions", headers=alice_headers)
    assert r.json() == []


def test_get_session_returns_details(client, alice_headers):
    sid = client.post("/sessions", json={}, headers=alice_headers).json()["id"]
    r = client.get(f"/sessions/{sid}", headers=alice_headers)
    assert r.status_code == 200
    assert r.json()["id"] == sid


def test_get_unknown_session_returns_404(client, alice_headers):
    r = client.get("/sessions/no-such-id", headers=alice_headers)
    assert r.status_code == 404


def test_user_cannot_access_another_users_session(client, alice_headers):
    """Bob ne doit pas pouvoir accéder aux sessions d'Alice."""
    sid = client.post("/sessions", json={}, headers=alice_headers).json()["id"]
    bob_token = client.post("/auth/signup", json={
        "email": "bob@test.com", "password": "bob12345",
    }).json()["token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    r = client.get(f"/sessions/{sid}", headers=bob_headers)
    assert r.status_code == 404  # pas 403 pour ne pas leak l'existence


def test_delete_session(client, alice_headers):
    sid = client.post("/sessions", json={}, headers=alice_headers).json()["id"]
    r = client.delete(f"/sessions/{sid}", headers=alice_headers)
    assert r.status_code == 204
    assert client.get(f"/sessions/{sid}", headers=alice_headers).status_code == 404


def test_end_session_returns_farewell(client, alice_headers):
    sid = client.post("/sessions", json={}, headers=alice_headers).json()["id"]
    r = client.post(f"/sessions/{sid}/end", headers=alice_headers)
    assert r.status_code == 200
    body = r.json()
    assert "Heureux" in body["farewell"] or "aider" in body["farewell"]
    # Vérif côté BDD : status passé à "ended"
    assert client.get(f"/sessions/{sid}", headers=alice_headers).json()["status"] == "ended"


def test_cannot_end_already_ended_session(client, alice_headers):
    sid = client.post("/sessions", json={}, headers=alice_headers).json()["id"]
    client.post(f"/sessions/{sid}/end", headers=alice_headers)
    r = client.post(f"/sessions/{sid}/end", headers=alice_headers)
    assert r.status_code == 400


def test_feedback_creation(client, alice_headers):
    sid = client.post("/sessions", json={}, headers=alice_headers).json()["id"]
    client.post(f"/sessions/{sid}/end", headers=alice_headers)
    r = client.post(f"/sessions/{sid}/feedback", headers=alice_headers,
                    json={"rating": 4, "comment": "Bien"})
    assert r.status_code == 201
    assert r.json()["rating"] == 4

    # Le rating apparaît dans /sessions
    sess = client.get("/sessions", headers=alice_headers).json()[0]
    assert sess["rating"] == 4


def test_feedback_rating_must_be_1_to_5(client, alice_headers):
    sid = client.post("/sessions", json={}, headers=alice_headers).json()["id"]
    assert client.post(f"/sessions/{sid}/feedback", headers=alice_headers,
                       json={"rating": 0}).status_code == 422
    assert client.post(f"/sessions/{sid}/feedback", headers=alice_headers,
                       json={"rating": 6}).status_code == 422


def test_cannot_feedback_twice(client, alice_headers):
    sid = client.post("/sessions", json={}, headers=alice_headers).json()["id"]
    client.post(f"/sessions/{sid}/feedback", headers=alice_headers, json={"rating": 5})
    r = client.post(f"/sessions/{sid}/feedback", headers=alice_headers, json={"rating": 3})
    assert r.status_code == 400


def test_anonymous_can_create_session(client, anon_headers):
    r = client.post("/sessions", json={}, headers=anon_headers)
    assert r.status_code == 201
    sessions = client.get("/sessions", headers=anon_headers).json()
    assert len(sessions) == 1

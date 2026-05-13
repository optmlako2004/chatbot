"""Tests d'authentification : signup, login, Google stub, anonyme, /auth/me."""


def test_signup_creates_user_and_returns_token(client):
    r = client.post("/auth/signup", json={
        "email": "new@test.com", "password": "secret123", "name": "New",
    })
    assert r.status_code == 201
    data = r.json()
    assert "token" in data
    assert data["user"]["email"] == "new@test.com"
    assert data["user"]["name"] == "New"
    assert data["user"]["is_anonymous"] is False


def test_signup_rejects_duplicate_email(client):
    payload = {"email": "dup@test.com", "password": "secret123"}
    client.post("/auth/signup", json=payload)
    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 400


def test_signup_validates_password_length(client):
    r = client.post("/auth/signup", json={"email": "a@b.com", "password": "12"})
    assert r.status_code == 422


def test_login_works_with_correct_password(client):
    client.post("/auth/signup", json={"email": "u@test.com", "password": "secret123"})
    r = client.post("/auth/login", json={"email": "u@test.com", "password": "secret123"})
    assert r.status_code == 200
    assert "token" in r.json()


def test_login_rejects_bad_password(client):
    client.post("/auth/signup", json={"email": "u@test.com", "password": "secret123"})
    r = client.post("/auth/login", json={"email": "u@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_login_rejects_unknown_email(client):
    r = client.post("/auth/login", json={"email": "ghost@test.com", "password": "x"})
    assert r.status_code == 401


def test_google_auth_stub_creates_user(client):
    r = client.post("/auth/google", json={
        "google_sub": "google-sub-xyz",
        "email": "g@test.com",
        "name": "Google User",
        "picture": "http://pic.url",
    })
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "g@test.com"


def test_google_auth_idempotent(client):
    payload = {"google_sub": "g1", "email": "g1@t.com", "name": "G1"}
    r1 = client.post("/auth/google", json=payload)
    r2 = client.post("/auth/google", json=payload)
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]


def test_google_auth_links_to_existing_email_account(client):
    """Si un user s'est inscrit en email/pwd puis se connecte via Google
    avec le même mail, on lie les comptes au lieu d'en créer un 2e."""
    client.post("/auth/signup", json={"email": "shared@test.com", "password": "secret123"})
    r = client.post("/auth/google", json={
        "google_sub": "g-shared", "email": "shared@test.com", "name": "S",
    })
    assert r.status_code == 200
    # Une 2e tentative Google retombe sur le même user
    r2 = client.post("/auth/google", json={
        "google_sub": "g-shared", "email": "shared@test.com", "name": "S",
    })
    assert r.json()["user"]["id"] == r2.json()["user"]["id"]


def test_anonymous_endpoint_returns_uuid(client):
    r = client.post("/auth/anonymous")
    assert r.status_code == 200
    assert "anonymous_id" in r.json()


def test_me_with_jwt(client, alice_headers):
    r = client.get("/auth/me", headers=alice_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "alice@test.com"


def test_me_with_anonymous_creates_user_on_the_fly(client, anon_headers):
    r = client.get("/auth/me", headers=anon_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["is_anonymous"] is True
    assert body["id"] == "test-anon-uuid-1234"


def test_me_without_auth_returns_401(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_invalid_jwt_returns_401(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer fake.jwt.token"})
    assert r.status_code == 401

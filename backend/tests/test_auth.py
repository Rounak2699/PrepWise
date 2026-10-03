from .conftest import auth_headers, register


def test_register_and_login(client):
    data = register(client, email="asha@example.com")
    assert data["user"]["email"] == "asha@example.com"
    assert data["user"]["onboarded"] is False
    assert "access_token" in data

    r = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "asha@example.com"


def test_duplicate_email_rejected(client):
    register(client, email="dup@example.com")
    r = client.post("/api/auth/register", json={"name": "Other", "email": "dup@example.com", "password": "password123"})
    assert r.status_code == 409


def test_login_wrong_password_rejected(client):
    register(client, email="wrongpw@example.com")
    r = client.post("/api/auth/login", json={"email": "wrongpw@example.com", "password": "not-it"})
    assert r.status_code == 401


def test_login_unknown_email_rejected(client):
    r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert r.status_code == 401


def test_password_too_short_rejected(client):
    r = client.post("/api/auth/register", json={"name": "X", "email": "short@example.com", "password": "abc"})
    assert r.status_code == 422


def test_protected_route_requires_token(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_email_is_case_insensitive_on_register(client):
    register(client, email="Case@Example.com")
    r = client.post("/api/auth/login", json={"email": "case@example.com", "password": "password123"})
    assert r.status_code == 200

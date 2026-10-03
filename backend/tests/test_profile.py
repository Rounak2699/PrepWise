from .conftest import auth_headers, register


def test_onboarding_sets_flag(client):
    data = register(client)
    H = auth_headers(data["access_token"])

    r = client.patch("/api/me", headers=H, json={
        "academic_year": "final-year", "branch": "CSE", "graduation_year": 2027, "target_role": "SDE",
        "preferences": {"difficulty": "hard", "preferred_topics": ["dsa", "oop"], "daily_question_count": 12},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["onboarded"] is True
    assert body["preferences"]["difficulty"] == "hard"
    assert body["preferences"]["preferred_topics"] == ["dsa", "oop"]


def test_invalid_difficulty_rejected(client):
    data = register(client)
    H = auth_headers(data["access_token"])
    r = client.patch("/api/me", headers=H, json={"preferences": {"difficulty": "impossible"}})
    assert r.status_code == 422


def test_unknown_topic_rejected(client):
    data = register(client)
    H = auth_headers(data["access_token"])
    r = client.patch("/api/me", headers=H, json={"preferences": {"preferred_topics": ["astrology"]}})
    assert r.status_code == 422


def test_partial_update_preserves_other_fields(client):
    data = register(client)
    H = auth_headers(data["access_token"])
    client.patch("/api/me", headers=H, json={"branch": "ECE"})
    r = client.patch("/api/me", headers=H, json={"target_role": "Backend Engineer"})
    body = r.json()
    assert body["branch"] == "ECE"
    assert body["target_role"] == "Backend Engineer"

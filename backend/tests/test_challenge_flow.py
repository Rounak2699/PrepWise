from sqlalchemy import select

from app.models import Question

from .conftest import auth_headers, register


def _onboard(client, H):
    client.patch("/api/me", headers=H, json={
        "academic_year": "final-year", "branch": "CSE", "graduation_year": 2027,
        "preferences": {"difficulty": "medium", "preferred_topics": ["dsa"]},
    })


def _answer_key(db_session) -> dict[int, str]:
    return {q.id: q.correct_answer for q in db_session.scalars(select(Question))}


def test_daily_challenge_created_lazily_and_hides_questions_until_started(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)

    r = client.get("/api/daily-challenge", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_started"
    assert body["questions"] is None
    assert 10 <= body["total_questions"] <= 15

    # Calling it again returns the same test, not a new one.
    r2 = client.get("/api/daily-challenge", headers=H)
    assert r2.json()["test_id"] == body["test_id"]


def test_start_reveals_questions_without_answers(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]

    r = client.post(f"/api/tests/{test_id}/start", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "in_progress"
    assert body["remaining_seconds"] > 0
    for q in body["questions"]:
        assert "correct_answer" not in q
        assert "explanation" not in q
        assert len(q["options"]) == 4


def test_full_submission_scores_deterministically(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]
    questions = client.post(f"/api/tests/{test_id}/start", headers=H).json()["questions"]
    answers = _answer_key(db_session)

    # Get the first half right, the rest wrong, to pin down an exact expected score.
    half = len(questions) // 2
    for i, q in enumerate(questions):
        correct = answers[q["id"]]
        wrong = next(c for c in "ABCD" if c != correct)
        chosen = correct if i < half else wrong
        r = client.post(f"/api/tests/{test_id}/response", headers=H, json={
            "question_id": q["id"], "selected_answer": chosen, "time_spent_seconds": 20,
        })
        assert r.status_code == 200

    result = client.post(f"/api/tests/{test_id}/submit", headers=H).json()
    assert result["score"] == half
    assert result["attempted"] == len(questions)
    assert result["unattempted"] == 0
    assert result["completion"] == 100.0
    assert result["accuracy"] == round(half / len(questions) * 100, 1)
    assert len(result["questions"]) == len(questions)
    # Review payload includes the answer key, unlike the in-progress view.
    assert all("correct_answer" in q and "explanation" in q for q in result["questions"])


def test_resubmitting_is_idempotent(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]
    client.post(f"/api/tests/{test_id}/start", headers=H)

    first = client.post(f"/api/tests/{test_id}/submit", headers=H).json()
    second = client.post(f"/api/tests/{test_id}/submit", headers=H).json()
    assert first["score"] == second["score"] == 0  # nothing answered
    assert first["completion"] == 0.0


def test_cannot_answer_after_submission(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]
    questions = client.post(f"/api/tests/{test_id}/start", headers=H).json()["questions"]
    client.post(f"/api/tests/{test_id}/submit", headers=H)

    r = client.post(f"/api/tests/{test_id}/response", headers=H, json={
        "question_id": questions[0]["id"], "selected_answer": "A", "time_spent_seconds": 5,
    })
    assert r.status_code == 409


def test_cannot_restart_a_submitted_test(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]
    client.post(f"/api/tests/{test_id}/start", headers=H)
    client.post(f"/api/tests/{test_id}/submit", headers=H)

    r = client.post(f"/api/tests/{test_id}/start", headers=H)
    assert r.status_code == 409


def test_result_unavailable_before_submission(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]
    client.post(f"/api/tests/{test_id}/start", headers=H)

    r = client.get(f"/api/tests/{test_id}/result", headers=H)
    assert r.status_code == 409


def test_response_rejects_foreign_question_id(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]
    client.post(f"/api/tests/{test_id}/start", headers=H)

    r = client.post(f"/api/tests/{test_id}/response", headers=H, json={
        "question_id": 999999, "selected_answer": "A", "time_spent_seconds": 5,
    })
    assert r.status_code == 400


def test_cannot_access_another_users_test(client, db_session):
    a = register(client, email="a@example.com")
    b = register(client, email="b@example.com")
    H_a = auth_headers(a["access_token"])
    H_b = auth_headers(b["access_token"])
    _onboard(client, H_a)
    _onboard(client, H_b)
    test_id_a = client.get("/api/daily-challenge", headers=H_a).json()["test_id"]

    r = client.post(f"/api/tests/{test_id_a}/start", headers=H_b)
    assert r.status_code == 404


def test_report_and_progress_after_submission(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]
    client.post(f"/api/tests/{test_id}/start", headers=H)
    client.post(f"/api/tests/{test_id}/submit", headers=H)

    report = client.get(f"/api/reports/{test_id}", headers=H)
    assert report.status_code == 200
    assert report.json()["narrative_source"] == "template"  # no AI key configured in tests

    progress = client.get("/api/progress", headers=H).json()
    assert progress["tests_completed"] == 1
    assert progress["current_streak"] == 1

    history = client.get("/api/tests/history", headers=H).json()
    assert len(history) == 1
    assert history[0]["test_id"] == test_id


def test_report_missing_before_submission(client, db_session):
    data = register(client)
    H = auth_headers(data["access_token"])
    _onboard(client, H)
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]

    r = client.get(f"/api/reports/{test_id}", headers=H)
    assert r.status_code == 404

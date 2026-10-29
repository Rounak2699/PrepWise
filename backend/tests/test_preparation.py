from datetime import date, timedelta

from sqlalchemy import select

from app.core.clock import today_local, utcnow
from app.models import Question, ReviewItem, StudyPlan, User
from app.services.spaced_repetition import review_interval

from .conftest import auth_headers, register


def test_study_plan_respects_daily_budget_and_weekdays(client):
    data = register(client)
    headers = auth_headers(data["access_token"])
    response = client.post("/api/study-plans", headers=headers, json={
        "goal": "General placement",
        "target_role": "Software Developer",
        "daily_minutes": 30,
        "duration_days": 14,
        "preferred_days": "weekdays",
        "current_level": "beginner",
        "target_topics": ["dsa", "dbms"],
    })
    assert response.status_code == 201, response.text
    plan = response.json()
    assert plan["daily_minutes"] == 30
    assert plan["status"] == "active"
    assert plan["days"]
    assert all(day["estimated_minutes"] <= 30 for day in plan["days"])
    assert all(task["estimated_minutes"] <= 30 for day in plan["days"] for task in day["tasks"])
    assert all(date.fromisoformat(day["date"]).weekday() < 5 for day in plan["days"])


def test_study_plan_task_completion_is_owned(client, db_session):
    first = register(client, email="plan-a@example.com")
    second = register(client, email="plan-b@example.com")
    plan = client.post("/api/study-plans", headers=auth_headers(first["access_token"]), json={
        "goal": "Coding improvement",
        "target_role": "Backend Developer",
        "daily_minutes": 60,
        "duration_days": 14,
    }).json()
    task_id = plan["days"][0]["tasks"][0]["id"]

    response = client.post(
        f"/api/study-plans/tasks/{task_id}/complete",
        headers=auth_headers(second["access_token"]),
    )
    assert response.status_code == 404
    completed = client.post(
        f"/api/study-plans/tasks/{task_id}/complete",
        headers=auth_headers(first["access_token"]),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_rebalance_moves_missed_tasks_within_daily_budget(client, db_session):
    data = register(client)
    headers = auth_headers(data["access_token"])
    plan_response = client.post("/api/study-plans", headers=headers, json={
        "goal": "General placement",
        "target_role": "Software Developer",
        "daily_minutes": 60,
        "duration_days": 14,
    })
    plan = db_session.get(StudyPlan, plan_response.json()["id"])
    yesterday = today_local() - timedelta(days=1)
    for day in plan.days:
        day.date = yesterday
    plan.end_date = yesterday
    db_session.commit()

    response = client.post(f"/api/study-plans/{plan.id}/regenerate", headers=headers)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["version"] == 2
    moved = [day for day in updated["days"] if day["date"] >= today_local().isoformat()]
    assert moved
    assert all(day["estimated_minutes"] <= 60 for day in moved)
    assert all(task["status"] == "pending" for day in moved for task in day["tasks"])


def test_review_intervals_follow_initial_scheduler_and_cap():
    assert [review_interval(result, 1, 0) for result in ("again", "hard", "good", "easy")] == [1, 2, 4, 8]
    assert review_interval("easy", 8, 1) == 16
    assert review_interval("easy", 90, 2) == 90


def test_submitted_test_adds_private_due_review_and_reschedules(client, db_session):
    data = register(client)
    headers = auth_headers(data["access_token"])
    daily = client.get("/api/daily-challenge", headers=headers).json()
    questions = client.post(f"/api/tests/{daily['test_id']}/start", headers=headers).json()["questions"]
    first_question = questions[0]
    question = db_session.get(Question, first_question["id"])
    wrong_answer = next(letter for letter in "ABCD" if letter != question.correct_answer)
    client.post(f"/api/tests/{daily['test_id']}/response", headers=headers, json={
        "question_id": question.id, "selected_answer": wrong_answer,
    })
    client.post(f"/api/tests/{daily['test_id']}/submit", headers=headers)

    item = db_session.scalar(select(ReviewItem).where(
        ReviewItem.user_id == data["user"]["id"],
        ReviewItem.source_question_id == question.id,
    ))
    assert item is not None
    assert item.interval_days == 1
    item.due_at = utcnow() - timedelta(seconds=1)
    db_session.commit()

    due = client.get("/api/reviews/due", headers=headers)
    assert due.status_code == 200
    review = next(row for row in due.json() if row["id"] == item.id)
    assert "correct_answer" not in review
    first = client.post(f"/api/reviews/{item.id}/submit", headers=headers, json={"result": "easy"})
    assert first.status_code == 200
    assert first.json()["interval_days"] == 8
    second = client.post(f"/api/reviews/{item.id}/submit", headers=headers, json={"result": "easy"})
    assert second.json()["interval_days"] == 16


def test_theme_defaults_to_system_and_persists(client):
    data = register(client)
    headers = auth_headers(data["access_token"])
    assert client.get("/api/preferences/theme", headers=headers).json() == {"theme": "system"}
    saved = client.patch("/api/preferences/theme", headers=headers, json={"theme": "dark"})
    assert saved.status_code == 200
    assert client.get("/api/preferences/theme", headers=headers).json() == {"theme": "dark"}
    assert client.patch("/api/preferences/theme", headers=headers, json={"theme": "sepia"}).status_code == 422


def test_company_pack_requires_verified_source_and_published_questions(client, db_session):
    data = register(client)
    headers = auth_headers(data["access_token"])
    assert client.post("/api/admin/companies", headers=headers, json={
        "name": "Example Systems", "slug": "example-systems",
    }).status_code == 403

    user = db_session.get(User, data["user"]["id"])
    user.role = "admin"
    db_session.commit()
    company = client.post("/api/admin/companies", headers=headers, json={
        "name": "Example Systems", "slug": "example-systems",
    })
    assert company.status_code == 201
    company_id = company.json()["id"]
    rejected = client.post(f"/api/admin/companies/{company_id}/packs", headers=headers, json={
        "role": "Software Developer", "title": "Developer practice",
        "items": [{"question_id": 1}],
    })
    assert rejected.status_code == 409
    secondary = client.post(f"/api/admin/companies/{company_id}/sources", headers=headers, json={
        "source_url": "https://reports.example.org/company",
        "source_title": "Supplementary report",
        "source_type": "reputable_secondary", "verified": True,
    })
    assert secondary.status_code == 201
    secondary_only_pack = client.post(f"/api/admin/companies/{company_id}/packs", headers=headers, json={
        "role": "Software Developer", "title": "Developer practice",
        "items": [{"question_id": 1}],
    })
    assert secondary_only_pack.status_code == 409

    source = client.post(f"/api/admin/companies/{company_id}/sources", headers=headers, json={
        "source_url": "https://careers.example.com/roles",
        "source_title": "Official careers page", "source_type": "official", "verified": True,
    })
    assert source.status_code == 201, source.text
    question = db_session.scalar(select(Question).where(Question.status == "published"))
    pack = client.post(f"/api/admin/companies/{company_id}/packs", headers=headers, json={
        "role": "Software Developer", "title": "Developer practice",
        "items": [{"question_id": question.id, "source_id": source.json()["id"]}],
    })
    assert pack.status_code == 201, pack.text
    public = client.get("/api/companies/example-systems", headers=headers).json()
    assert any(source["source_type"] == "official" for source in public["sources"])
    packs = client.get("/api/companies/example-systems/packs", headers=headers).json()
    content = client.post(f"/api/company-packs/{packs[0]['id']}/start", headers=headers).json()
    assert "correct_answer" not in content["questions"][0]
    assert "not actual or leaked" in content["practice_content_notice"]
    question_id = content["questions"][0]["id"]
    question = db_session.get(Question, question_id)
    answer = client.post(f"/api/company-packs/{packs[0]['id']}/answer", headers=headers, json={
        "question_id": question_id, "selected_answer": question.correct_answer,
    })
    assert answer.status_code == 200
    assert answer.json()["is_correct"] is True
    assert answer.json()["completed_at"] is not None
    assert client.get("/api/company-packs/my", headers=headers).json()[0]["answered"] == 1

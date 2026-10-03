"""One-shot smoke test: register -> onboard -> take the daily test -> submit -> result -> report -> progress."""
import sys
import time

import requests

B = "http://127.0.0.1:8123"


def check(label, resp, expect=200):
    ok = resp.status_code == expect
    print(f"{'OK ' if ok else 'FAIL'} {label} -> {resp.status_code}")
    if not ok:
        print("   ", resp.text[:500])
        sys.exit(1)
    return resp.json()


email = f"asha{int(time.time())}@example.com"
r = requests.post(f"{B}/api/auth/register", json={"name": "Asha Rao", "email": email, "password": "password123"})
data = check("register", r, 201)
token = data["access_token"]
H = {"Authorization": f"Bearer {token}"}
assert data["user"]["onboarded"] is False

r = requests.patch(f"{B}/api/me", headers=H, json={
    "academic_year": "final-year", "branch": "CSE", "graduation_year": 2027, "target_role": "SDE",
    "preferences": {"difficulty": "medium", "preferred_topics": ["dsa", "oop"]},
})
me = check("onboard", r)
assert me["onboarded"] is True

r = requests.get(f"{B}/api/daily-challenge", headers=H)
challenge = check("daily-challenge (not started)", r)
assert challenge["status"] == "not_started" and challenge["questions"] is None
test_id = challenge["test_id"]

r = requests.post(f"{B}/api/tests/{test_id}/start", headers=H)
started = check("start test", r)
assert started["status"] == "in_progress"
questions = started["questions"]
assert len(questions) == challenge["total_questions"]
bad_labels = [q["category_label"] for q in questions if q["category_label"] != q["category_label"].strip() or q["category_label"].islower()]
print("   category labels seen:", sorted({q["category_label"] for q in questions}))
assert all(len(q["category_label"]) > 2 and not q["category_label"].isupper() for q in questions)

# Fetch the answer key straight from the DB to simulate a student getting most of them right.
import sqlite3  # noqa: E402
conn = sqlite3.connect("placement.db")
answers = dict(conn.execute("SELECT id, correct_answer FROM questions").fetchall())
conn.close()

for i, q in enumerate(questions):
    correct = answers[q["id"]]
    chosen = correct if i % 4 != 0 else "A"  # get ~75% right, deliberately miss every 4th
    r = requests.post(f"{B}/api/tests/{test_id}/response", headers=H, json={
        "question_id": q["id"], "selected_answer": chosen, "time_spent_seconds": 30 + i,
    })
    check(f"answer q{q['id']}", r)

r = requests.post(f"{B}/api/tests/{test_id}/submit", headers=H)
result = check("submit", r)
print(f"   score={result['score']}/{result['total']} accuracy={result['accuracy']} completion={result['completion']}")
assert result["status"] == "submitted"

r = requests.post(f"{B}/api/tests/{test_id}/submit", headers=H)  # idempotency check
result2 = check("re-submit (idempotent)", r)
assert result2["score"] == result["score"], "resubmitting must not change the score"

r = requests.get(f"{B}/api/tests/{test_id}/result", headers=H)
check("get result", r)

r = requests.get(f"{B}/api/reports/{test_id}", headers=H)
report = check("get AI report", r)
print("   report summary:", report["summary"][:120])
print("   narrative_source:", report["narrative_source"])

r = requests.get(f"{B}/api/progress", headers=H)
progress = check("get progress", r)
print("   progress:", {k: progress[k] for k in ("tests_completed", "current_streak", "overall_accuracy")})

r = requests.get(f"{B}/api/progress/topics", headers=H)
topics = check("get topic progress", r)
print("   topic rows:", len(topics))

r = requests.get(f"{B}/api/tests/history", headers=H)
history = check("get history", r)
print("   history rows:", len(history))

# Trying to start an already-submitted test must fail cleanly.
r = requests.post(f"{B}/api/tests/{test_id}/start", headers=H)
check("start already-submitted test (expect 409)", r, 409)

# Wrong password must be rejected.
r = requests.post(f"{B}/api/auth/login", json={"email": email, "password": "wrong-password"})
check("login with wrong password (expect 401)", r, 401)

# No token must be rejected.
r = requests.get(f"{B}/api/me")
check("no-auth access (expect 401)", r, 401)

print("\nALL CHECKS PASSED")

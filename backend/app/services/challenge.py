import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.clock import today_local
from ..core.config import settings
from ..models import Question, Test, TestQuestion, TopicPerformance, User
from ..taxonomy import DIFFICULTIES

FIXED_SLOTS = ["quantitative"] * 3 + ["logical"] * 2 + ["verbal"] + ["dsa"] * 2
ROTATING = ["oop", "dbms", "os", "networks", "software-eng"]


def _slots(count: int, rotation: int, preferred: list[str]) -> list[str]:
    slots = FIXED_SLOTS[:count]
    extra = count - len(slots)
    if extra > 0:
        rot = ROTATING[rotation % len(ROTATING):] + ROTATING[: rotation % len(ROTATING)]
        # preferred categories get first claim on the rotating slots
        rot = [c for c in rot if c in preferred] + [c for c in rot if c not in preferred]
        slots += [rot[i % len(rot)] for i in range(extra)]
    return slots


def _recent_question_ids(db: Session, user_id: int, today) -> set[int]:
    since = today - timedelta(days=settings.recent_window_days)
    rows = db.execute(
        select(TestQuestion.question_id).join(Test, Test.id == TestQuestion.test_id)
        .where(Test.user_id == user_id, Test.date >= since)
    )
    return {qid for (qid,) in rows}


def build_question_set(db: Session, user: User, today) -> list[Question]:
    prefs = user.preferences
    count = prefs.daily_question_count if prefs else settings.default_question_count
    target = DIFFICULTIES.index(prefs.difficulty) if prefs and prefs.difficulty in DIFFICULTIES else 1
    rng = random.Random(user.id * 1_000_003 + today.toordinal())

    pool = list(db.scalars(select(Question).where(Question.status == "published")))
    recent = _recent_question_ids(db, user.id, today)
    weak = {
        t.topic
        for t in db.scalars(select(TopicPerformance).where(TopicPerformance.user_id == user.id))
        if t.attempted >= 2 and t.correct / t.attempted < 0.6
    }

    chosen: list[Question] = []
    used: set[int] = set()
    for category in _slots(count, today.toordinal() + user.id, prefs.preferred_topics if prefs else []):
        candidates = [q for q in pool if q.category == category and q.id not in used]
        if not candidates:
            continue
        candidates.sort(key=lambda q: (
            q.id in recent,                                   # avoid recent repeats
            abs(DIFFICULTIES.index(q.difficulty) - target),   # stay near preferred difficulty
            q.topic not in weak,                              # lean toward weak topics
            rng.random(),
        ))
        pick = candidates[0]
        chosen.append(pick)
        used.add(pick.id)

    rng.shuffle(chosen)
    return chosen


def get_or_create_daily_test(db: Session, user: User) -> Test:
    today = today_local()
    test = db.scalar(select(Test).where(Test.user_id == user.id, Test.date == today))
    if test:
        return test

    questions = build_question_set(db, user, today)
    if not questions:
        raise RuntimeError("No published questions available. Run the seed script.")

    test = Test(user_id=user.id, date=today, total_questions=len(questions), status="not_started",
                duration_seconds=len(questions) * settings.seconds_per_question)
    test.items = [TestQuestion(question_id=q.id, sequence_no=i + 1) for i, q in enumerate(questions)]
    db.add(test)
    try:
        db.commit()
    except IntegrityError:  # two tabs raced; return the winner
        db.rollback()
        return db.scalar(select(Test).where(Test.user_id == user.id, Test.date == today))
    return test

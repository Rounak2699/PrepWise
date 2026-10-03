"""Deterministic scoring. Nothing in here calls an AI model."""
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.clock import today_local, utcnow
from ..models import PerformanceSnapshot, Response, Streak, Test, TopicPerformance
from . import report as report_service


def _update_streak(db: Session, user_id: int, test_date) -> None:
    streak = db.get(Streak, user_id)
    if streak is None:
        streak = Streak(user_id=user_id, current_streak=0, longest_streak=0)
        db.add(streak)
    last = streak.last_activity_date
    if last == test_date:
        return
    if last is not None and test_date - last == timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1
    streak.longest_streak = max(streak.longest_streak, streak.current_streak)
    streak.last_activity_date = test_date


def submit_test(db: Session, test: Test, auto: bool = False) -> Test:
    """Lock the attempt and compute the score. Idempotent: a submitted test is returned untouched."""
    if test.status == "submitted":
        return test

    responses = {r.question_id: r for r in db.scalars(select(Response).where(Response.test_id == test.id))}
    per_topic: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0])  # attempted, correct, time
    score = attempted = total_time = 0

    for item in test.items:
        q = item.question
        r = responses.get(q.id)
        if r is None:
            r = Response(test_id=test.id, question_id=q.id)
            db.add(r)
        if r.selected_answer:
            attempted += 1
            r.is_correct = r.selected_answer == q.correct_answer
            score += int(r.is_correct)
            total_time += r.time_spent_seconds
            stat = per_topic[(q.category, q.topic)]
            stat[0] += 1
            stat[1] += int(r.is_correct)
            stat[2] += r.time_spent_seconds
        else:
            r.is_correct = None

    total = test.total_questions
    now = utcnow()
    test.status = "submitted"
    test.submitted_at = now
    test.auto_submitted = auto

    db.add(PerformanceSnapshot(
        user_id=test.user_id, test_id=test.id, score=score, total=total,
        accuracy=round(score / attempted * 100, 1) if attempted else 0.0,
        completion=round(attempted / total * 100, 1) if total else 0.0,
        attempted_count=attempted,
        average_time=round(total_time / attempted, 1) if attempted else 0.0,
    ))

    for (category, topic), (att, cor, tm) in per_topic.items():
        row = db.scalar(select(TopicPerformance).where(TopicPerformance.user_id == test.user_id, TopicPerformance.topic == topic))
        if row is None:
            row = TopicPerformance(user_id=test.user_id, category=category, topic=topic, attempted=0, correct=0, total_time=0)
            db.add(row)
        row.attempted += att
        row.correct += cor
        row.total_time += tm
        row.last_attempted_at = now

    _update_streak(db, test.user_id, test.date)
    db.flush()
    report_service.create_report(db, test)

    try:
        db.commit()
    except IntegrityError:  # a concurrent request already submitted this test
        db.rollback()
        test = db.get(Test, test.id)
    return test


def expire_if_needed(db: Session, test: Test) -> Test:
    """Auto-submit an in-progress attempt whose time has run out."""
    from ..core.config import settings
    if test.status == "in_progress" and test.started_at:
        deadline = test.started_at + timedelta(seconds=test.duration_seconds + settings.submit_grace_seconds)
        if utcnow() > deadline:
            return submit_test(db, test, auto=True)
    return test


__all__ = ["submit_test", "expire_if_needed", "today_local"]

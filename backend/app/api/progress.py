from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import PerformanceSnapshot, Streak, TopicPerformance, User
from ..schemas import ProgressOut, TopicProgress
from ..taxonomy import category_label, topic_label
from .deps import get_current_user

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("", response_model=ProgressOut)
def get_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    snaps = list(db.scalars(
        select(PerformanceSnapshot).where(PerformanceSnapshot.user_id == user.id).order_by(PerformanceSnapshot.created_at)
    ))
    streak = db.get(Streak, user.id)
    topics = list(db.scalars(select(TopicPerformance).where(TopicPerformance.user_id == user.id)))

    attempted_total = sum(t.attempted for t in topics)
    correct_total = sum(t.correct for t in topics)
    time_total = sum(t.total_time for t in topics)
    recent = snaps[-5:]

    return ProgressOut(
        tests_completed=len(snaps),
        current_streak=streak.current_streak if streak else 0,
        longest_streak=streak.longest_streak if streak else 0,
        questions_attempted=attempted_total,
        overall_accuracy=round(correct_total / attempted_total * 100, 1) if attempted_total else 0.0,
        average_time=round(time_total / attempted_total, 1) if attempted_total else 0.0,
        latest_percentage=round(snaps[-1].score / snaps[-1].total * 100, 1) if snaps and snaps[-1].total else None,
        recent_average_percentage=(
            round(sum(s.score / s.total * 100 for s in recent if s.total) / len(recent), 1) if recent else None
        ),
        trend=[
            {"date": s.created_at.date().isoformat(), "percentage": round(s.score / s.total * 100, 1) if s.total else 0}
            for s in snaps[-30:]
        ],
    )


@router.get("/topics", response_model=list[TopicProgress])
def get_topic_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(TopicPerformance).where(TopicPerformance.user_id == user.id))
    return [
        TopicProgress(
            topic=r.topic, label=topic_label(r.topic), category=r.category,
            category_label=category_label(r.category),
            attempted=r.attempted, correct=r.correct,
            accuracy=round(r.correct / r.attempted * 100, 1) if r.attempted else 0.0,
            avg_time=round(r.total_time / r.attempted, 1) if r.attempted else 0.0,
            last_attempted_at=r.last_attempted_at,
        )
        for r in rows
    ]

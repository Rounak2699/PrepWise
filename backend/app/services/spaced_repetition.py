from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.clock import utcnow
from ..models import Question, ReviewItem

MAX_REVIEW_INTERVAL = 90


def review_interval(result: str, previous_interval: int, prior_easy_count: int) -> int:
    if result == "again":
        return 1
    if result == "hard":
        return 2
    if result == "good":
        return 4
    if result == "easy":
        interval = min(MAX_REVIEW_INTERVAL, previous_interval * 2) if prior_easy_count else 8
        return max(1, interval)
    raise ValueError(f"Unsupported review result: {result}")


def create_review_items(db: Session, user_id: int, responses: list[tuple[Question, bool]]) -> None:
    """Make answered, published test questions available for future review."""
    for question, correct in responses:
        item = db.scalar(select(ReviewItem).where(
            ReviewItem.user_id == user_id, ReviewItem.source_question_id == question.id
        ))
        if item is None:
            interval = 4 if correct else 1
            db.add(ReviewItem(
                user_id=user_id, source_question_id=question.id,
                concept_key=f"{question.category}:{question.topic}",
                topic=question.topic, state="new", interval_days=interval,
                due_at=utcnow() + timedelta(days=interval),
            ))

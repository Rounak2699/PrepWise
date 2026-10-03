from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.clock import utcnow
from ..core.db import get_db
from ..models import Response, Test, User
from ..schemas import ChallengeOut, HistoryItem, QuestionPublic, ResponseIn, ResultOut, TopicStat
from ..services import evaluation
from ..services.challenge import get_or_create_daily_test
from ..taxonomy import category_label, topic_label
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["challenge"])


def _remaining_seconds(test: Test) -> int | None:
    if test.status != "in_progress" or test.started_at is None:
        return None
    elapsed = (utcnow() - test.started_at).total_seconds()
    return max(0, int(test.duration_seconds - elapsed))


def _questions_public(db: Session, test: Test) -> list[QuestionPublic]:
    responses = {r.question_id: r for r in db.scalars(select(Response).where(Response.test_id == test.id))}
    out = []
    for item in test.items:
        q = item.question
        r = responses.get(q.id)
        out.append(QuestionPublic(
            id=q.id, sequence_no=item.sequence_no, type=q.type, category=q.category,
            category_label=category_label(q.category), topic=q.topic, difficulty=q.difficulty,
            prompt=q.prompt, options=q.options_json,
            selected_answer=r.selected_answer if r else None,
            marked_for_review=r.marked_for_review if r else False,
            time_spent_seconds=r.time_spent_seconds if r else 0,
        ))
    return out


def _challenge_out(db: Session, test: Test, with_questions: bool) -> ChallengeOut:
    return ChallengeOut(
        test_id=test.id, date=test.date, status=test.status, duration_seconds=test.duration_seconds,
        total_questions=test.total_questions, started_at=test.started_at,
        remaining_seconds=_remaining_seconds(test), server_time=utcnow(),
        questions=_questions_public(db, test) if with_questions else None,
    )


def _get_owned_test(db: Session, user: User, test_id: int) -> Test:
    test = db.get(Test, test_id)
    if test is None or test.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test not found")
    return evaluation.expire_if_needed(db, test)


@router.get("/daily-challenge", response_model=ChallengeOut)
def daily_challenge(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test = get_or_create_daily_test(db, user)
    test = evaluation.expire_if_needed(db, test)
    return _challenge_out(db, test, with_questions=test.status != "not_started")


@router.post("/tests/{test_id}/start", response_model=ChallengeOut)
def start_test(test_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test = _get_owned_test(db, user, test_id)
    if test.status == "submitted":
        raise HTTPException(status.HTTP_409_CONFLICT, "This test has already been submitted")
    if test.status == "not_started":
        test.status = "in_progress"
        test.started_at = utcnow()
        db.commit()
    return _challenge_out(db, test, with_questions=True)


@router.post("/tests/{test_id}/response", response_model=QuestionPublic)
def save_response(test_id: int, payload: ResponseIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test = _get_owned_test(db, user, test_id)
    if test.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "Test is not in progress")
    if payload.question_id not in {i.question_id for i in test.items}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Question does not belong to this test")

    r = db.scalar(select(Response).where(Response.test_id == test_id, Response.question_id == payload.question_id))
    if r is None:
        r = Response(test_id=test_id, question_id=payload.question_id, time_spent_seconds=0)
        db.add(r)
    r.selected_answer = payload.selected_answer
    r.time_spent_seconds = max(r.time_spent_seconds or 0, payload.time_spent_seconds)
    r.marked_for_review = payload.marked_for_review
    db.commit()

    item = next(i for i in test.items if i.question_id == payload.question_id)
    q = item.question
    return QuestionPublic(
        id=q.id, sequence_no=item.sequence_no, type=q.type, category=q.category,
        category_label=category_label(q.category), topic=q.topic, difficulty=q.difficulty,
        prompt=q.prompt, options=q.options_json, selected_answer=r.selected_answer,
        marked_for_review=r.marked_for_review, time_spent_seconds=r.time_spent_seconds,
    )


@router.post("/tests/{test_id}/submit", response_model=ResultOut)
def submit_test(test_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test = _get_owned_test(db, user, test_id)
    if test.status == "not_started":
        raise HTTPException(status.HTTP_409_CONFLICT, "Test has not been started")
    test = evaluation.submit_test(db, test)
    return _result_out(db, test)


def _result_out(db: Session, test: Test) -> ResultOut:
    from ..models import PerformanceSnapshot, TopicPerformance

    snap = db.scalar(select(PerformanceSnapshot).where(PerformanceSnapshot.test_id == test.id))
    responses = {r.question_id: r for r in db.scalars(select(Response).where(Response.test_id == test.id))}

    questions = []
    by_topic: dict[str, list] = {}
    for item in test.items:
        q = item.question
        r = responses.get(q.id)
        selected = r.selected_answer if r else None
        is_correct = bool(r and r.is_correct)
        questions.append(dict(
            id=q.id, sequence_no=item.sequence_no, category=q.category, category_label=category_label(q.category),
            topic=q.topic, difficulty=q.difficulty, prompt=q.prompt, options=q.options_json,
            selected_answer=selected, correct_answer=q.correct_answer, is_correct=is_correct,
            explanation=q.explanation, time_spent_seconds=r.time_spent_seconds if r else 0,
        ))
        stat = by_topic.setdefault(q.topic, {"category": q.category, "attempted": 0, "correct": 0})
        if selected:
            stat["attempted"] += 1
            stat["correct"] += int(is_correct)

    topics = [
        TopicStat(topic=t, label=topic_label(t), category=s["category"], attempted=s["attempted"], correct=s["correct"],
                  accuracy=round(s["correct"] / s["attempted"] * 100, 1) if s["attempted"] else 0.0)
        for t, s in by_topic.items() if s["attempted"]
    ]

    return ResultOut(
        test_id=test.id, date=test.date, status=test.status, auto_submitted=test.auto_submitted,
        score=snap.score if snap else 0, total=test.total_questions,
        percentage=round((snap.score / test.total_questions) * 100, 1) if snap and test.total_questions else 0.0,
        accuracy=snap.accuracy if snap else 0.0, completion=snap.completion if snap else 0.0,
        attempted=snap.attempted_count if snap else 0,
        unattempted=test.total_questions - (snap.attempted_count if snap else 0),
        average_time=snap.average_time if snap else 0.0, topics=topics, questions=questions,
    )


@router.get("/tests/{test_id}/result", response_model=ResultOut)
def get_result(test_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test = _get_owned_test(db, user, test_id)
    if test.status != "submitted":
        raise HTTPException(status.HTTP_409_CONFLICT, "Test has not been submitted yet")
    return _result_out(db, test)


@router.get("/tests/history", response_model=list[HistoryItem])
def history(limit: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from ..models import PerformanceSnapshot

    tests = db.scalars(
        select(Test).where(Test.user_id == user.id).order_by(Test.date.desc()).limit(min(limit, 90))
    ).all()
    snaps = {
        s.test_id: s for s in db.scalars(
            select(PerformanceSnapshot).where(PerformanceSnapshot.test_id.in_([t.id for t in tests]))
        )
    } if tests else {}
    return [
        HistoryItem(
            test_id=t.id, date=t.date, status=t.status, total=t.total_questions,
            score=snaps[t.id].score if t.id in snaps else None,
            accuracy=snaps[t.id].accuracy if t.id in snaps else None,
            completion=snaps[t.id].completion if t.id in snaps else None,
        )
        for t in tests
    ]

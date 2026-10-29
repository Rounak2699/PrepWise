from datetime import date, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..core.clock import today_local, utcnow
from ..core.db import get_db
from ..models import (
    Company, CompanyPack, CompanyPackEnrollment, CompanyPackItem, CompanySource,
    CompanyPackResponse, CompanyPackVersion, Question, ReviewAttempt, ReviewItem, ReviewSetting,
    StudyPlan, StudyPlanDay, StudyPlanEvent, StudyPlanTask, TopicPerformance, User,
)
from ..schemas import (
    CompanyCreateIn, CompanyPackCreateIn, CompanySourceCreateIn,
    CompanyPackAnswerIn, ReviewSubmitIn, StudyPlanIn, StudyPlanUpdate, ThemeIn,
)
from ..services.spaced_repetition import review_interval
from ..taxonomy import CATEGORIES, topic_label
from .deps import get_current_user, require_admin

router = APIRouter(tags=["personalized preparation"])


def _plan_data(plan: StudyPlan) -> dict:
    return {
        "id": plan.id,
        "goal": plan.goal,
        "target_role": plan.target_role,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "daily_minutes": plan.daily_minutes,
        "status": plan.status,
        "version": plan.version,
        "preferred_days": plan.preferred_days,
        "current_level": plan.current_level,
        "topics": plan.topics_json,
        "days": [
            {
                "id": day.id,
                "date": day.date,
                "focus": day.focus,
                "estimated_minutes": day.estimated_minutes,
                "status": day.status,
                "reason": day.reason,
                "tasks": [
                    {
                        "id": task.id,
                        "task_type": task.task_type,
                        "topic": task.topic,
                        "difficulty": task.difficulty,
                        "estimated_minutes": task.estimated_minutes,
                        "status": task.status,
                        "completed_at": task.completed_at,
                    }
                    for task in day.tasks
                ],
            }
            for day in sorted(plan.days, key=lambda row: row.date)
        ],
    }


def _active_plan(db: Session, user_id: int) -> StudyPlan | None:
    return db.scalar(
        select(StudyPlan)
        .options(selectinload(StudyPlan.days).selectinload(StudyPlanDay.tasks))
        .where(StudyPlan.user_id == user_id, StudyPlan.status == "active")
        .order_by(StudyPlan.id.desc())
    )


def _build_plan(db: Session, user: User, payload: StudyPlanIn, start: date) -> StudyPlan:
    topics = payload.target_topics or (user.preferences.preferred_topics if user.preferences else [])
    topics = [topic for topic in topics if topic in CATEGORIES]
    if not topics:
        topics = list(CATEGORIES)
    stats = list(db.scalars(select(TopicPerformance).where(TopicPerformance.user_id == user.id)))
    accuracy = {row.topic: row.correct / row.attempted for row in stats if row.attempted}
    topics.sort(key=lambda topic: (accuracy.get(topic, 0.65), topic))
    difficulty = {"beginner": "easy", "intermediate": "medium", "advanced": "hard"}[payload.current_level]
    plan = StudyPlan(
        user_id=user.id,
        goal=payload.goal.strip(),
        target_role=payload.target_role.strip(),
        start_date=start,
        end_date=start + timedelta(days=payload.duration_days - 1),
        daily_minutes=payload.daily_minutes,
        preferred_days=payload.preferred_days,
        current_level=payload.current_level,
        topics_json=topics,
    )
    scheduled = 0
    for offset in range(payload.duration_days):
        day_date = start + timedelta(days=offset)
        if payload.preferred_days == "weekdays" and day_date.weekday() >= 5:
            continue
        scheduled += 1
        sequence = scheduled - 1
        if sequence > 0 and sequence % 7 == 6:
            task_type, topic, focus = "mock", "mixed", "Weekly assessment"
            reason = "A weekly mock helps measure progress without changing deterministic test scoring."
            minutes = payload.daily_minutes
        elif sequence > 0 and sequence % 6 == 5:
            task_type, topic, focus = "revision", topics[(sequence // 6) % len(topics)], "Spaced revision"
            reason = "A dedicated review session reinforces topics already covered."
            minutes = min(30, payload.daily_minutes)
        else:
            topic = topics[sequence % len(topics)]
            task_type, focus = "practice", topic_label(topic)
            if topic in accuracy and accuracy[topic] < 0.6:
                reason = "Prioritized because recent recorded accuracy is below 60%."
            elif topic not in accuracy:
                reason = "Included to build coverage for your selected preparation topics."
            else:
                reason = "Balances topic practice with the rest of your selected plan."
            minutes = min(payload.daily_minutes, max(15, payload.daily_minutes * 3 // 4))
        day = StudyPlanDay(
            date=day_date, focus=focus, estimated_minutes=minutes,
            reason=reason,
            tasks=[StudyPlanTask(
                task_type=task_type, topic=topic, difficulty=difficulty,
                estimated_minutes=minutes,
            )],
        )
        plan.days.append(day)
    return plan


@router.post("/api/study-plans", status_code=status.HTTP_201_CREATED)
def create_study_plan(
    payload: StudyPlanIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    previous = _active_plan(db, user.id)
    if previous:
        previous.status = "paused"
        db.add(StudyPlanEvent(
            plan_id=previous.id, event_type="superseded",
            old_value="active", new_value="paused",
        ))
    plan = _build_plan(db, user, payload, today_local())
    db.add(plan)
    db.flush()
    db.add(StudyPlanEvent(plan_id=plan.id, event_type="created", new_value=str(plan.version)))
    db.commit()
    return _plan_data(_active_plan(db, user.id))


@router.get("/api/study-plans/current")
def get_current_study_plan(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = _active_plan(db, user.id)
    return _plan_data(plan) if plan else None


@router.patch("/api/study-plans/{plan_id}")
def update_study_plan(
    plan_id: int,
    payload: StudyPlanUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.get(StudyPlan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Study plan not found")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        old = getattr(plan, field)
        if old != value:
            db.add(StudyPlanEvent(
                plan_id=plan.id, event_type=f"updated_{field}",
                old_value=str(old), new_value=str(value),
            ))
            setattr(plan, field, value)
    if "daily_minutes" in changes:
        for day in plan.days:
            if day.date >= today_local() and day.status != "completed":
                for task in day.tasks:
                    if task.status == "pending":
                        task.estimated_minutes = min(task.estimated_minutes, plan.daily_minutes)
                day.estimated_minutes = sum(task.estimated_minutes for task in day.tasks)
    db.commit()
    return _plan_data(_active_plan(db, user.id) if plan.status == "active" else plan)


@router.post("/api/study-plans/{plan_id}/regenerate")
def regenerate_study_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.scalar(
        select(StudyPlan)
        .options(selectinload(StudyPlan.days).selectinload(StudyPlanDay.tasks))
        .where(StudyPlan.id == plan_id, StudyPlan.user_id == user.id)
    )
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Study plan not found")
    today = today_local()
    missed = [
        task for day in plan.days if day.date < today
        for task in day.tasks if task.status == "pending"
    ]
    for task in missed:
        previous_day = task.day
        destination = next(
            (day for day in sorted(plan.days, key=lambda row: row.date)
             if day.date >= today and day.estimated_minutes + task.estimated_minutes <= plan.daily_minutes),
            None,
        )
        if destination is None:
            next_date = max(today, plan.end_date + timedelta(days=1))
            destination = StudyPlanDay(
                date=next_date, focus="Rebalanced study",
                estimated_minutes=0, reason="Added to make room for a missed task.",
            )
            plan.days.append(destination)
            plan.end_date = next_date
        task.day = destination
        previous_day.estimated_minutes = max(0, previous_day.estimated_minutes - task.estimated_minutes)
        destination.estimated_minutes += task.estimated_minutes
    db.flush()
    plan.version += 1
    db.add(StudyPlanEvent(
        plan_id=plan.id, event_type="regenerated",
        old_value=str(plan.version - 1), new_value=str(plan.version),
    ))
    db.commit()
    db.refresh(plan)
    return _plan_data(plan)


@router.post("/api/study-plans/tasks/{task_id}/complete")
def complete_study_plan_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.scalar(
        select(StudyPlanTask).join(StudyPlanDay).join(StudyPlan)
        .where(StudyPlanTask.id == task_id, StudyPlan.user_id == user.id)
    )
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Study task not found")
    if task.status != "completed":
        task.status = "completed"
        task.completed_at = utcnow()
        task.day.status = "completed" if all(t.status == "completed" for t in task.day.tasks) else "in_progress"
        db.commit()
    return {"id": task.id, "status": task.status, "completed_at": task.completed_at}


@router.get("/api/reviews/due")
def get_due_reviews(
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    setting = db.get(ReviewSetting, user.id)
    if setting and not setting.enabled:
        return []
    effective_limit = min(limit, setting.daily_limit if setting else 20)
    items = db.scalars(
        select(ReviewItem)
        .options(selectinload(ReviewItem.question))
        .where(ReviewItem.user_id == user.id, ReviewItem.due_at <= utcnow())
        .order_by(ReviewItem.due_at, ReviewItem.state)
        .limit(effective_limit)
    ).all()
    return [
        {
            "id": item.id, "topic": item.topic, "state": item.state,
            "due_at": item.due_at, "prompt": item.question.prompt,
            "options": item.question.options_json,
        }
        for item in items if item.question.status == "published"
    ]


@router.post("/api/reviews/{review_id}/submit")
def submit_review(
    review_id: int,
    payload: ReviewSubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(ReviewItem).options(selectinload(ReviewItem.question))
        .where(ReviewItem.id == review_id, ReviewItem.user_id == user.id)
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review item not found")
    question = item.question
    if question.status != "published":
        raise HTTPException(status.HTTP_409_CONFLICT, "This question is no longer available for review")
    now = utcnow()
    previous_easy_count = db.query(ReviewAttempt).filter(
        ReviewAttempt.review_item_id == item.id, ReviewAttempt.result == "easy"
    ).count()
    item.interval_days = review_interval(payload.result, item.interval_days, previous_easy_count)
    item.state = "learning" if payload.result in {"again", "hard"} else "review"
    item.last_reviewed_at = now
    item.due_at = now + timedelta(days=item.interval_days)
    if payload.result == "again":
        item.ease_factor = max(1.3, item.ease_factor - 0.2)
    elif payload.result == "easy":
        item.ease_factor = min(3.0, item.ease_factor + 0.15)
    db.add(ReviewAttempt(
        review_item_id=item.id, result=payload.result, response_time=payload.response_time,
        reviewed_at=now,
    ))
    db.commit()
    return {
        "id": item.id, "result": payload.result, "next_due_at": item.due_at,
        "interval_days": item.interval_days, "correct_answer": question.correct_answer,
        "explanation": question.explanation,
    }


@router.get("/api/reviews/stats")
def get_review_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = list(db.scalars(select(ReviewItem).where(ReviewItem.user_id == user.id)))
    today = utcnow()
    return {
        "total": len(items),
        "due": sum(item.due_at <= today for item in items),
        "forgotten": sum(item.state == "learning" for item in items),
        "completed_attempts": db.query(ReviewAttempt).join(ReviewItem).filter(ReviewItem.user_id == user.id).count(),
    }


def _verified_source(source: CompanySource) -> bool:
    parsed = urlparse(source.source_url)
    return parsed.scheme == "https" and bool(parsed.netloc) and source.verified_at is not None


def _current_source(source: CompanySource) -> bool:
    return _verified_source(source) and source.verified_at >= utcnow() - timedelta(days=365)


def _current_official_source(source: CompanySource) -> bool:
    return _current_source(source) and source.source_type == "official"


def _pack_has_current_official_source(db: Session, pack: CompanyPack) -> bool:
    sources = db.scalars(select(CompanySource).where(
        CompanySource.company_id == pack.company_id
    ))
    return any(_current_official_source(source) for source in sources)


@router.post("/api/admin/companies", status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    company = Company(
        name=payload.name.strip(), slug=payload.slug,
        website=str(payload.website) if payload.website else None,
        description=payload.description, status="active",
    )
    db.add(company)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A company with this name or slug already exists")
    db.refresh(company)
    return {"id": company.id, "name": company.name, "slug": company.slug}


@router.post("/api/admin/companies/{company_id}/sources", status_code=status.HTTP_201_CREATED)
def add_company_source(
    company_id: int,
    payload: CompanySourceCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if urlparse(str(payload.source_url)).scheme != "https":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Company sources must use HTTPS")
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    source = CompanySource(
        company_id=company.id, source_url=str(payload.source_url),
        source_title=payload.source_title.strip(), source_type=payload.source_type,
        notes=payload.notes, verified_at=utcnow() if payload.verified else None,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {
        "id": source.id, "source_url": source.source_url,
        "source_title": source.source_title, "source_type": source.source_type,
        "verified_at": source.verified_at,
    }


@router.post("/api/admin/companies/{company_id}/packs", status_code=status.HTTP_201_CREATED)
def create_company_pack(
    company_id: int,
    payload: CompanyPackCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    company = db.scalar(
        select(Company).options(selectinload(Company.sources))
        .where(Company.id == company_id, Company.status == "active")
    )
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    company_sources = list(db.scalars(
        select(CompanySource).where(CompanySource.company_id == company.id)
    ))
    if not any(_current_official_source(source) for source in company_sources):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Add a recently verified HTTPS source before publishing company practice packs",
        )
    question_ids = {item.question_id for item in payload.items}
    questions = {
        question.id: question
        for question in db.scalars(select(Question).where(
            Question.id.in_(question_ids), Question.status == "published"
        ))
    }
    if len(questions) != len(question_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Every pack item must reference a published question")
    source_ids = {item.source_id for item in payload.items if item.source_id is not None}
    sources = {
        source.id: source for source in company_sources
        if source.id in source_ids and _current_source(source)
    }
    if len(sources) != len(source_ids):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Practice item source references must belong to this company and be recently verified",
        )
    latest_verified = max(
        source.verified_at for source in company_sources if _current_official_source(source)
    )
    previous = db.scalar(
        select(CompanyPack).options(selectinload(CompanyPack.versions))
        .where(CompanyPack.company_id == company.id, CompanyPack.role == payload.role.strip())
        .order_by(CompanyPack.version.desc())
    )
    version = previous.version + 1 if previous else 1
    if previous:
        previous.status = "archived"
        for previous_version in previous.versions:
            if previous_version.archived_at is None:
                previous_version.archived_at = utcnow()
    pack = CompanyPack(
        company_id=company.id, role=payload.role.strip(), title=payload.title.strip(),
        version=version, status="published", last_verified_at=latest_verified,
        items=[
            CompanyPackItem(
                item_type="practice", topic=questions[item.question_id].topic,
                difficulty=questions[item.question_id].difficulty,
                question_ref=item.question_id, source_ref=item.source_id,
            )
            for item in payload.items
        ],
        versions=[CompanyPackVersion(version=version)],
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return {"id": pack.id, "version": pack.version, "status": pack.status}


@router.get("/api/companies")
def search_companies(
    q: str = Query(default="", max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    companies = db.scalars(
        select(Company)
        .where(Company.status == "active", Company.name.ilike(f"%{q.strip()}%"))
        .order_by(Company.name).limit(50)
    ).all()
    company_ids = [company.id for company in companies]
    sources = db.scalars(
        select(CompanySource).where(CompanySource.company_id.in_(company_ids))
    ).all() if company_ids else []
    sources_by_company: dict[int, list[CompanySource]] = {}
    for source in sources:
        sources_by_company.setdefault(source.company_id, []).append(source)
    return [
        {
            "id": company.id, "name": company.name, "slug": company.slug,
            "website": company.website if any(_current_official_source(source) for source in sources_by_company.get(company.id, [])) else None,
            "description": company.description if any(_current_official_source(source) for source in sources_by_company.get(company.id, [])) else None,
            "last_verified_at": max(
                (source.verified_at for source in sources_by_company.get(company.id, []) if _verified_source(source)),
                default=None,
            ),
        }
        for company in companies
    ]


@router.get("/api/companies/{slug}")
def get_company(
    slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = db.scalar(select(Company).where(Company.slug == slug, Company.status == "active"))
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    company_sources = list(db.scalars(
        select(CompanySource).where(CompanySource.company_id == company.id)
    ))
    current_sources = [source for source in company_sources if _current_official_source(source)]
    return {
        "id": company.id, "name": company.name, "slug": company.slug,
        "website": company.website if current_sources else None,
        "description": company.description if current_sources else None,
        "facts_outdated": any(
            _verified_source(source) and source.source_type == "official"
            for source in company_sources
        ) and not current_sources,
        "sources": [
            {
                "id": source.id, "source_url": source.source_url,
                "source_title": source.source_title, "source_type": source.source_type,
                "retrieved_at": source.retrieved_at, "verified_at": source.verified_at,
                "notes": source.notes,
                "outdated": not _current_source(source),
            }
            for source in sorted(
                (source for source in company_sources if _verified_source(source)),
                key=lambda source: (source.source_type == "official", source.verified_at),
                reverse=True,
            )
        ],
    }


@router.get("/api/companies/{slug}/packs")
def get_company_packs(
    slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = db.scalar(select(Company).where(Company.slug == slug, Company.status == "active"))
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    company_sources = list(db.scalars(
        select(CompanySource).where(CompanySource.company_id == company.id)
    ))
    packs = db.scalars(
        select(CompanyPack).options(selectinload(CompanyPack.items))
        .where(
            CompanyPack.company_id == company.id, CompanyPack.status == "published",
            CompanyPack.last_verified_at >= utcnow() - timedelta(days=365),
        )
        .order_by(CompanyPack.role, CompanyPack.version.desc())
    ).all()
    if not any(_current_official_source(source) for source in company_sources):
        packs = []
    return [
        {
            "id": pack.id, "role": pack.role, "title": pack.title,
            "version": pack.version, "last_verified_at": pack.last_verified_at,
            "practice_content_notice": "Generated practice content, not actual or leaked company questions.",
        }
        for pack in packs
    ]


@router.post("/api/company-packs/{pack_id}/start")
def start_company_pack(
    pack_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pack = db.scalar(
        select(CompanyPack).options(
            selectinload(CompanyPack.items)
        ).where(CompanyPack.id == pack_id, CompanyPack.status == "published")
    )
    if pack is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company practice pack not found")
    if (
        pack.last_verified_at is None
        or pack.last_verified_at < utcnow() - timedelta(days=365)
        or not _pack_has_current_official_source(db, pack)
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "This pack's sources need re-verification before it can be used")
    enrollment = db.scalar(select(CompanyPackEnrollment).where(
        CompanyPackEnrollment.user_id == user.id, CompanyPackEnrollment.pack_id == pack.id
    ))
    if enrollment is None:
        enrollment = CompanyPackEnrollment(user_id=user.id, pack_id=pack.id)
        db.add(enrollment)
        db.commit()
    questions = []
    responses = {
        row.question_id: row for row in db.scalars(select(CompanyPackResponse).where(
            CompanyPackResponse.user_id == user.id, CompanyPackResponse.pack_id == pack.id
        ))
    }
    for item in pack.items:
        question = db.get(Question, item.question_ref) if item.question_ref else None
        if question and question.status == "published":
            response = responses.get(question.id)
            questions.append({
                "id": question.id, "topic": question.topic, "difficulty": question.difficulty,
                "type": question.type, "prompt": question.prompt, "options": question.options_json,
                "selected_answer": response.selected_answer if response else None,
                "is_correct": response.is_correct if response else None,
                "explanation": question.explanation if response else None,
            })
    enrollment.completed_at = utcnow() if questions and all(
        question["is_correct"] is not None for question in questions
    ) else None
    db.commit()
    return {
        "pack_id": pack.id, "title": pack.title, "role": pack.role,
        "completed": enrollment.completed_at is not None,
        "practice_content_notice": "These are practice questions, not actual or leaked company questions.",
        "questions": questions,
    }


@router.post("/api/company-packs/{pack_id}/answer")
def answer_company_pack_question(
    pack_id: int,
    payload: CompanyPackAnswerIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pack = db.get(CompanyPack, pack_id)
    if pack is None or pack.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company practice pack not found")
    if (
        pack.last_verified_at is None
        or pack.last_verified_at < utcnow() - timedelta(days=365)
        or not _pack_has_current_official_source(db, pack)
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "This pack's sources need re-verification before it can be used")
    enrollment = db.scalar(select(CompanyPackEnrollment).where(
        CompanyPackEnrollment.user_id == user.id, CompanyPackEnrollment.pack_id == pack.id
    ))
    if enrollment is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Start this practice pack before answering questions")
    pack_item = db.scalar(select(CompanyPackItem).where(
        CompanyPackItem.pack_id == pack.id, CompanyPackItem.question_ref == payload.question_id
    ))
    question = db.get(Question, payload.question_id)
    if pack_item is None or question is None or question.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question is not part of this practice pack")

    answer = db.scalar(select(CompanyPackResponse).where(
        CompanyPackResponse.user_id == user.id,
        CompanyPackResponse.pack_id == pack.id,
        CompanyPackResponse.question_id == question.id,
    ))
    if answer is None:
        answer = CompanyPackResponse(
            user_id=user.id, pack_id=pack.id, question_id=question.id,
            selected_answer=payload.selected_answer,
            is_correct=payload.selected_answer == question.correct_answer,
        )
        db.add(answer)
    else:
        answer.selected_answer = payload.selected_answer
        answer.is_correct = payload.selected_answer == question.correct_answer
        answer.submitted_at = utcnow()
    db.flush()
    published_question_ids = set(db.scalars(
        select(CompanyPackItem.question_ref).join(Question, Question.id == CompanyPackItem.question_ref)
        .where(CompanyPackItem.pack_id == pack.id, Question.status == "published")
    ))
    answered_ids = set(db.scalars(select(CompanyPackResponse.question_id).where(
        CompanyPackResponse.user_id == user.id,
        CompanyPackResponse.pack_id == pack.id,
        CompanyPackResponse.question_id.in_(published_question_ids),
    ))) if published_question_ids else set()
    if published_question_ids and published_question_ids.issubset(answered_ids):
        enrollment.completed_at = utcnow()
    db.commit()
    return {
        "question_id": question.id, "selected_answer": answer.selected_answer,
        "is_correct": answer.is_correct, "correct_answer": question.correct_answer,
        "explanation": question.explanation, "completed_at": enrollment.completed_at,
    }


@router.get("/api/company-packs/my")
def get_my_company_pack_progress(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enrollments = db.scalars(
        select(CompanyPackEnrollment).where(CompanyPackEnrollment.user_id == user.id)
        .order_by(CompanyPackEnrollment.started_at.desc())
    ).all()
    results = []
    for enrollment in enrollments:
        pack = db.get(CompanyPack, enrollment.pack_id)
        if pack is None:
            continue
        total = db.query(CompanyPackItem).join(
            Question, Question.id == CompanyPackItem.question_ref
        ).filter(CompanyPackItem.pack_id == pack.id, Question.status == "published").count()
        answered = db.query(CompanyPackResponse).filter(
            CompanyPackResponse.user_id == user.id,
            CompanyPackResponse.pack_id == pack.id,
        ).count()
        results.append({
            "pack_id": pack.id, "title": pack.title, "role": pack.role,
            "started_at": enrollment.started_at, "completed_at": enrollment.completed_at,
            "answered": answered, "total": total,
        })
    return results


@router.get("/api/company-packs/{pack_id}/sources")
def get_pack_sources(
    pack_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pack = db.get(CompanyPack, pack_id)
    if pack is None or pack.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company practice pack not found")
    if (
        pack.last_verified_at is None
        or pack.last_verified_at < utcnow() - timedelta(days=365)
        or not _pack_has_current_official_source(db, pack)
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "This pack's sources need re-verification before use")
    sources = db.scalars(
        select(CompanySource).where(CompanySource.company_id == pack.company_id)
        .order_by(CompanySource.verified_at.desc(), CompanySource.source_type)
    ).all()
    return [
        {
            "source_url": source.source_url, "source_title": source.source_title,
            "source_type": source.source_type, "retrieved_at": source.retrieved_at,
            "verified_at": source.verified_at, "outdated": not _current_source(source),
        }
        for source in sources if _verified_source(source)
    ]


def _get_theme_preference(user: User) -> str:
    settings = user.preferences.notification_settings if user.preferences else {}
    theme = settings.get("theme", "system") if isinstance(settings, dict) else "system"
    return theme if theme in {"light", "dark", "system"} else "system"


@router.get("/api/preferences/theme")
def get_theme(user: User = Depends(get_current_user)):
    return {"theme": _get_theme_preference(user)}


@router.patch("/api/preferences/theme")
def update_theme(
    payload: ThemeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.preferences is None:
        from ..models import UserPreference
        user.preferences = UserPreference()
    preferences = dict(user.preferences.notification_settings or {})
    preferences["theme"] = payload.theme
    user.preferences.notification_settings = preferences
    db.commit()
    return {"theme": payload.theme}

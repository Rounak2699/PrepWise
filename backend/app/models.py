from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.clock import utcnow
from .core.db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="student")  # student | admin
    academic_year: Mapped[str | None] = mapped_column(String(40), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(120), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    preferences: Mapped["UserPreference"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    preferred_topics: Mapped[list] = mapped_column(JSON, default=list)  # list of category slugs
    daily_question_count: Mapped[int] = mapped_column(Integer, default=12)
    notification_settings: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="preferences")


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(20), default="mcq")
    category: Mapped[str] = mapped_column(String(40), index=True)
    topic: Mapped[str] = mapped_column(String(60), index=True)
    subtopic: Mapped[str | None] = mapped_column(String(60), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options_json: Mapped[list] = mapped_column(JSON)
    correct_answer: Mapped[str] = mapped_column(String(4))  # "A".."D" — never sent to clients before submission
    explanation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)  # draft|validated|published|rejected
    generation_source: Mapped[str] = mapped_column(String(20), default="seed")  # seed|ai|manual
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Test(Base):
    __tablename__ = "tests"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_test_user_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    total_questions: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="not_started")  # not_started|in_progress|submitted
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_submitted: Mapped[bool] = mapped_column(Boolean, default=False)

    items: Mapped[list["TestQuestion"]] = relationship(order_by="TestQuestion.sequence_no", cascade="all, delete-orphan")


class TestQuestion(Base):
    __tablename__ = "test_questions"
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    sequence_no: Mapped[int] = mapped_column(Integer)

    question: Mapped[Question] = relationship()


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("test_id", "question_id", name="uq_response_test_question"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    selected_answer: Mapped[str | None] = mapped_column(String(4), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    marked_for_review: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), unique=True)
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    accuracy: Mapped[float] = mapped_column(Float)
    completion: Mapped[float] = mapped_column(Float)
    attempted_count: Mapped[int] = mapped_column(Integer)
    average_time: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TopicPerformance(Base):
    __tablename__ = "topic_performance"
    __table_args__ = (UniqueConstraint("user_id", "topic", name="uq_topic_user"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    topic: Mapped[str] = mapped_column(String(60))
    attempted: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    total_time: Mapped[int] = mapped_column(Integer, default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AIReport(Base):
    __tablename__ = "ai_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    strengths_json: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses_json: Mapped[list] = mapped_column(JSON, default=list)
    recommendations_json: Mapped[list] = mapped_column(JSON, default=list)
    narrative_source: Mapped[str] = mapped_column(String(20), default="template")  # template|ai
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Streak(Base):
    __tablename__ = "streaks"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    goal: Mapped[str] = mapped_column(String(80))
    target_role: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    daily_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    preferred_days: Mapped[str] = mapped_column(String(20), default="daily")
    current_level: Mapped[str] = mapped_column(String(20), default="intermediate")
    topics_json: Mapped[list] = mapped_column(JSON, default=list)
    days: Mapped[list["StudyPlanDay"]] = relationship(
        cascade="all, delete-orphan", order_by="StudyPlanDay.date"
    )


class StudyPlanDay(Base):
    __tablename__ = "study_plan_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("study_plans.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    focus: Mapped[str] = mapped_column(String(80))
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reason: Mapped[str] = mapped_column(Text, default="")
    tasks: Mapped[list["StudyPlanTask"]] = relationship(
        back_populates="day", cascade="all, delete-orphan"
    )


class StudyPlanTask(Base):
    __tablename__ = "study_plan_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("study_plan_days.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(20))
    topic: Mapped[str] = mapped_column(String(80))
    difficulty: Mapped[str] = mapped_column(String(20))
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    day: Mapped["StudyPlanDay"] = relationship(back_populates="tasks")


class StudyPlanEvent(Base):
    __tablename__ = "study_plan_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("study_plans.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (UniqueConstraint("user_id", "source_question_id", name="uq_review_user_question"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    concept_key: Mapped[str] = mapped_column(String(120))
    topic: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(20), default="new")
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.0)
    due_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    question: Mapped[Question] = relationship()


class ReviewAttempt(Base):
    __tablename__ = "review_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_item_id: Mapped[int] = mapped_column(ForeignKey("review_items.id"), index=True)
    result: Mapped[str] = mapped_column(String(20))
    response_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ReviewSetting(Base):
    __tablename__ = "review_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=20)
    preferred_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    sources: Mapped[list["CompanySource"]] = relationship(cascade="all, delete-orphan")
    packs: Mapped[list["CompanyPack"]] = relationship(cascade="all, delete-orphan")


class CompanySource(Base):
    __tablename__ = "company_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    source_title: Mapped[str] = mapped_column(String(250))
    source_type: Mapped[str] = mapped_column(String(30))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CompanyPack(Base):
    __tablename__ = "company_packs"
    __table_args__ = (UniqueConstraint("company_id", "role", "version", name="uq_company_pack_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    role: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(180))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items: Mapped[list["CompanyPackItem"]] = relationship(cascade="all, delete-orphan")
    versions: Mapped[list["CompanyPackVersion"]] = relationship(cascade="all, delete-orphan")


class CompanyPackItem(Base):
    __tablename__ = "company_pack_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("company_packs.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(30))
    topic: Mapped[str] = mapped_column(String(80))
    difficulty: Mapped[str] = mapped_column(String(20))
    question_ref: Mapped[int | None] = mapped_column(ForeignKey("questions.id"), nullable=True)
    source_ref: Mapped[int | None] = mapped_column(ForeignKey("company_sources.id"), nullable=True)


class CompanyPackVersion(Base):
    __tablename__ = "company_pack_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("company_packs.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CompanyPackEnrollment(Base):
    __tablename__ = "company_pack_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "pack_id", name="uq_company_pack_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("company_packs.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CompanyPackResponse(Base):
    __tablename__ = "company_pack_responses"
    __table_args__ = (
        UniqueConstraint("user_id", "pack_id", "question_id", name="uq_company_pack_response"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("company_packs.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    selected_answer: Mapped[str] = mapped_column(String(4))
    is_correct: Mapped[bool] = mapped_column(Boolean)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

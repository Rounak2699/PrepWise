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

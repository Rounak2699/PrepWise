from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .taxonomy import CATEGORIES, DIFFICULTIES

Letter = Literal["A", "B", "C", "D"]


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def lower(cls, v: str) -> str:
        return v.lower()


class LoginIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lower(cls, v: str) -> str:
        return v.lower()


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    difficulty: str
    preferred_topics: list[str]
    daily_question_count: int


class PreferencesIn(BaseModel):
    difficulty: str | None = None
    preferred_topics: list[str] | None = None
    daily_question_count: int | None = Field(default=None, ge=10, le=15)

    @field_validator("difficulty")
    @classmethod
    def _diff(cls, v):
        if v is not None and v not in DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {DIFFICULTIES}")
        return v

    @field_validator("preferred_topics")
    @classmethod
    def _topics(cls, v):
        if v is not None:
            bad = [t for t in v if t not in CATEGORIES]
            if bad:
                raise ValueError(f"unknown topics: {bad}")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    academic_year: str | None
    branch: str | None
    graduation_year: int | None
    target_role: str | None
    onboarded: bool
    preferences: PreferencesOut


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    academic_year: str | None = Field(default=None, max_length=40)
    branch: str | None = Field(default=None, max_length=120)
    graduation_year: int | None = Field(default=None, ge=2020, le=2040)
    target_role: str | None = Field(default=None, max_length=120)
    preferences: PreferencesIn | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class QuestionPublic(BaseModel):
    """Question as shown during an attempt. Deliberately has no answer or explanation."""
    id: int
    sequence_no: int
    type: str
    category: str
    category_label: str
    topic: str
    difficulty: str
    prompt: str
    options: list[str]
    selected_answer: str | None = None
    marked_for_review: bool = False
    time_spent_seconds: int = 0


class ChallengeOut(BaseModel):
    test_id: int
    date: date
    status: str
    duration_seconds: int
    total_questions: int
    started_at: datetime | None
    remaining_seconds: int | None
    server_time: datetime
    questions: list[QuestionPublic] | None = None  # only present while in progress


class ResponseIn(BaseModel):
    question_id: int
    selected_answer: Letter | None = None
    time_spent_seconds: int = Field(default=0, ge=0, le=3600)
    marked_for_review: bool = False


class QuestionReview(BaseModel):
    id: int
    sequence_no: int
    category: str
    category_label: str
    topic: str
    difficulty: str
    prompt: str
    options: list[str]
    selected_answer: str | None
    correct_answer: str
    is_correct: bool
    explanation: str
    time_spent_seconds: int


class TopicStat(BaseModel):
    topic: str
    label: str
    category: str
    attempted: int
    correct: int
    accuracy: float


class ResultOut(BaseModel):
    test_id: int
    date: date
    status: str
    auto_submitted: bool
    score: int
    total: int
    percentage: float
    accuracy: float
    completion: float
    attempted: int
    unattempted: int
    average_time: float
    topics: list[TopicStat]
    questions: list[QuestionReview]


class HistoryItem(BaseModel):
    test_id: int
    date: date
    status: str
    score: int | None
    total: int
    accuracy: float | None
    completion: float | None


class ReportOut(BaseModel):
    test_id: int
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    narrative_source: str
    created_at: datetime


class ProgressOut(BaseModel):
    tests_completed: int
    current_streak: int
    longest_streak: int
    questions_attempted: int
    overall_accuracy: float
    average_time: float
    latest_percentage: float | None
    recent_average_percentage: float | None
    trend: list[dict]


class TopicProgress(BaseModel):
    topic: str
    label: str
    category: str
    category_label: str
    attempted: int
    correct: int
    accuracy: float
    avg_time: float
    last_attempted_at: datetime | None

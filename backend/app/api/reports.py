from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import AIReport, Test, User
from ..schemas import ReportOut
from .deps import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{test_id}", response_model=ReportOut)
def get_report(test_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test = db.get(Test, test_id)
    if test is None or test.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test not found")
    report = db.scalar(select(AIReport).where(AIReport.test_id == test_id))
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not available yet — submit the test first")
    return ReportOut(
        test_id=report.test_id, summary=report.summary, strengths=report.strengths_json,
        weaknesses=report.weaknesses_json, recommendations=report.recommendations_json,
        narrative_source=report.narrative_source, created_at=report.created_at,
    )

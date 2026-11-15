from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from insights_service.database import get_db
from insights_service.schemas.insight_change import InsightChangeOut
from insights_service.schemas.student_insight import (
    CurrentStudentInsightsOut, StudentInsightOut, StudentInsightSummaryOut,
)
from insights_service.services.insight_change_service import InsightChangeService
from insights_service.services.student_insight_service import StudentInsightService

router = APIRouter(prefix="/student-insights", tags=["student_insights"])


@router.get("/current", response_model=CurrentStudentInsightsOut)
def search_current_insights(
    group_ids: list[int] | None = Query(None),
    student_ids: list[int] | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return StudentInsightService(db).search_current(group_ids, student_ids, limit, offset)


@router.get("/{student_id}", response_model=StudentInsightOut)
def get_student_insight(student_id: int, db: Session = Depends(get_db)):
    insight = StudentInsightService(db).get_latest(student_id)
    if insight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No insights for this student")
    return insight


@router.get("/{student_id}/history", response_model=list[StudentInsightSummaryOut])
def get_student_insight_history(
    student_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return StudentInsightService(db).get_history(student_id, limit)


@router.get("/{student_id}/changes", response_model=list[InsightChangeOut])
def get_student_changes(
    student_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return InsightChangeService(db).get_for_student(student_id, limit)

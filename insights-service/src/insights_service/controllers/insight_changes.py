from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from insights_service.database import get_db
from insights_service.schemas.insight_change import CurrentInsightChangesOut
from insights_service.services.insight_change_service import InsightChangeService

router = APIRouter(prefix="/insight-changes", tags=["insight_changes"])


@router.get("/latest", response_model=CurrentInsightChangesOut)
def get_latest_changes(
    worsened_only: bool = False,
    group_ids: list[int] | None = Query(None),
    db: Session = Depends(get_db),
):
    return InsightChangeService(db).get_latest(worsened_only, group_ids)

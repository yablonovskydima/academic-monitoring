from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from insights_service.database import get_db
from insights_service.schemas.group_summary import CurrentGroupSummariesOut
from insights_service.services.group_summary_service import GroupSummaryService

router = APIRouter(prefix="/group-summaries", tags=["group_summaries"])


@router.get("/latest", response_model=CurrentGroupSummariesOut)
def get_latest_group_summaries(
    group_ids: list[int] | None = Query(None),
    db: Session = Depends(get_db),
):
    return GroupSummaryService(db).get_latest(group_ids)

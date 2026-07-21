from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.services.group_service import GroupService
from import_service.schemas.group import GroupOut, GroupFull

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/", response_model=list[GroupOut])
def get_groups(db: Session = Depends(get_db)):
    return GroupService(db).get_all()


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = GroupService(db).get_by_id(group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.get("/{group_id}/full", response_model=GroupFull)
def get_group_full(group_id: int, db: Session = Depends(get_db)):
    group = GroupService(db).get_full(group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group
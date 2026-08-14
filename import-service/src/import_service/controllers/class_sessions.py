from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.services.class_session_service import ClassSessionService
from import_service.schemas.class_session import ClassSessionOut, ClassSessionFull

router = APIRouter(prefix="/class-sessions", tags=["class_sessions"])


@router.get("/{session_id}", response_model=ClassSessionOut)
def get_class_session(session_id: int, db: Session = Depends(get_db)):
    class_session = ClassSessionService(db).get_by_id(session_id)
    if class_session is None:
        raise HTTPException(status_code=404, detail="Class session not found")
    return class_session


@router.get("/{session_id}/full", response_model=ClassSessionFull)
def get_class_session_full(session_id: int, db: Session = Depends(get_db)):
    class_session = ClassSessionService(db).get_full(session_id)
    if class_session is None:
        raise HTTPException(status_code=404, detail="Class session not found")
    return class_session


@router.get("/by-offering/{offering_id}", response_model=list[ClassSessionOut])
def get_sessions_by_offering(offering_id: int, db: Session = Depends(get_db)):
    return ClassSessionService(db).get_by_offering(offering_id)
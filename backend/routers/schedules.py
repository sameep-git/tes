from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

@router.get("/", response_model=List[schemas.ScheduleResponse])
def get_schedules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    schedules = (
        db.query(models.Schedule)
        .options(
            joinedload(models.Schedule.sections)
            .joinedload(models.Section.course),
            joinedload(models.Schedule.sections)
            .joinedload(models.Section.professor),
            joinedload(models.Schedule.sections)
            .joinedload(models.Section.timeslot),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [schemas.ScheduleResponse.from_orm_with_relations(s) for s in schedules]

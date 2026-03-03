from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/timeslots", tags=["timeslots"])


@router.get("/", response_model=List[schemas.TimeSlotResponse])
def get_timeslots(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    q = db.query(models.TimeSlot)
    if active_only:
        q = q.filter(models.TimeSlot.active == True)
    return q.order_by(models.TimeSlot.days, models.TimeSlot.start_time).all()

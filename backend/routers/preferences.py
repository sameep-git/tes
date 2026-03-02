from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/preferences", tags=["preferences"])

@router.get("/", response_model=List[schemas.PreferenceResponse])
def get_preferences(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    preferences = (
        db.query(models.Preference)
        .options(joinedload(models.Preference.professor))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return preferences

@router.put("/{pref_id}/approve", response_model=schemas.PreferenceResponse)
def approve_preference(pref_id: int, db: Session = Depends(get_db)):
    pref = db.query(models.Preference).filter(models.Preference.id == pref_id).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    pref.admin_approved = True
    db.commit()
    db.refresh(pref)
    # Eagerly load professor for response
    db.refresh(pref, attribute_names=["professor"])
    return pref

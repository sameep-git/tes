from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/preferences", tags=["preferences"])

@router.get("/", response_model=List[schemas.PreferenceResponse])
def get_preferences(
    semester: Optional[str] = None,
    year: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(models.Preference).options(
        joinedload(models.Preference.professor)
    )
    if semester:
        q = q.filter(func.lower(models.Preference.semester) == semester.lower())
    if year is not None:
        q = q.filter(models.Preference.year == year)
    return q.offset(skip).limit(limit).all()


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


class PatchPreferenceBody(BaseModel):
    parsed_json: Optional[dict] = None


@router.patch("/{pref_id}", response_model=schemas.PreferenceResponse)
def update_preference(pref_id: int, body: PatchPreferenceBody, db: Session = Depends(get_db)):
    pref = db.query(models.Preference).filter(models.Preference.id == pref_id).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    if body.parsed_json is not None:
        pref.parsed_json = body.parsed_json
        pref.admin_approved = False  # reset approval after manual edits
    db.commit()
    db.refresh(pref)
    db.refresh(pref, attribute_names=["professor"])
    return pref

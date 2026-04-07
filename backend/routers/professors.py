from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/professors", tags=["professors"])

@router.get("/", response_model=List[schemas.ProfessorResponse])
def get_professors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    professors = db.query(models.Professor).offset(skip).limit(limit).all()
    return professors

@router.get("/{prof_id}", response_model=schemas.ProfessorResponse)
def get_professor(prof_id: int, db: Session = Depends(get_db)):
    professor = db.query(models.Professor).filter(models.Professor.id == prof_id).first()
    if not professor:
        raise HTTPException(status_code=404, detail=f"Professor with ID {prof_id} not found.")
    return professor
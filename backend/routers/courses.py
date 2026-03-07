from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/courses", tags=["courses"])

@router.get("/", response_model=List[schemas.CourseResponse])
def get_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    courses = db.query(models.Course).offset(skip).limit(limit).all()
    return courses

@router.get("/{course_id}/history", response_model=List[schemas.SectionResponse])
def get_course_history(
    course_id: int, 
    semester: str = None, 
    year: int = None, 
    db: Session = Depends(get_db)
):
    query = db.query(models.Section).join(models.Schedule).filter(
        models.Section.course_id == course_id,
        models.Schedule.status == "Finalized" # Only show finalized history
    )
    
    if semester:
        query = query.filter(models.Schedule.semester == semester)
    if year:
        query = query.filter(models.Schedule.year == year)
        
    # Sort by year descending, then semester
    sections = query.order_by(
        models.Schedule.year.desc(), 
        models.Schedule.semester.asc()
    ).all()
    
    return [schemas.SectionResponse.from_orm_with_relations(s) for s in sections]

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/courses", tags=["courses"])

@router.get("/", response_model=List[schemas.CourseResponse])
def get_courses(
    semester: Optional[str] = None,
    year: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    query = db.query(models.Course)
    if semester:
        query = query.filter(models.Course.semester == semester)
    if year:
        query = query.filter(models.Course.year == year)
        
    courses = query.offset(skip).limit(limit).all()
    return courses

@router.get("/{course_id}/history", response_model=List[schemas.SectionResponse])
def get_course_history(
    course_id: int, 
    semester: Optional[str] = None, 
    year: Optional[int] = None, 
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

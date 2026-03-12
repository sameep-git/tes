from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from .. import models, schemas

from sqlalchemy import func

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
    if semester is not None:
        query = query.filter(func.lower(models.Course.semester) == semester.lower())
    if year is not None:
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
    # Get the course to find its code
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return []

    # Find all courses with the same code to get cross-term history
    matching_course_ids = db.query(models.Course.id).filter(models.Course.code == course.code)

    query = db.query(models.Section).join(models.Schedule).filter(
        models.Section.course_id.in_(matching_course_ids),
        models.Schedule.status == "Finalized" # Only show finalized history
    )
    
    if semester is not None:
        query = query.filter(func.lower(models.Schedule.semester) == semester.lower())
    if year is not None:
        query = query.filter(models.Schedule.year == year)
        
    # Sort by year descending, then semester
    sections = query.order_by(
        models.Schedule.year.desc(), 
        models.Schedule.semester.asc()
    ).all()
    
    return [schemas.SectionResponse.from_orm_with_relations(s) for s in sections]

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
    
    if semester is not None and year is not None:
        exact_match_query = query.filter(
            func.lower(models.Course.semester) == semester.lower(),
            models.Course.year == year
        )
        exact_matches = exact_match_query.offset(skip).limit(limit).all()
        
        if len(exact_matches) > 0:
            return exact_matches
            
        # AUTO-CLONE LOGIC: if requested semester has no specific courses cloned yet,
        # we will fetch all CourseTemplates and clone them into the Course table.
        templates = db.query(models.CourseTemplate).all()
        if templates:
            new_courses = []
            for t in templates:
                new_course = models.Course(
                    template_id=t.id,
                    code=t.code,
                    name=t.name,
                    semester=semester.capitalize(),
                    year=year,
                    credits=t.credits,
                    level=t.level,
                    min_sections=t.default_min_sections,
                    max_sections=t.default_max_sections,
                    capacity=t.default_capacity,
                    core_ssc=t.core_ssc,
                    core_ht=t.core_ht,
                    core_ga=t.core_ga,
                    core_wem=t.core_wem
                )
                new_courses.append(new_course)
            
            db.add_all(new_courses)
            db.commit()
            
            # Re-fetch after commit to ensure IDs and relationships are populated
            return exact_match_query.offset(skip).limit(limit).all()

    # If no specific filter (or no templates to clone), just return them
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

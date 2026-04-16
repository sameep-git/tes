from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
    """Return courses, optionally filtered by semester and/or year. Pure read."""
    query = db.query(models.Course)
    if semester is not None:
        query = query.filter(func.lower(models.Course.semester) == semester.lower())
    if year is not None:
        query = query.filter(models.Course.year == year)
    return query.offset(skip).limit(limit).all()


@router.post("/initialize/", response_model=List[schemas.CourseResponse])
def initialize_courses(
    semester: str,
    year: int,
    db: Session = Depends(get_db)
):
    """
    Idempotent: clone all CourseTemplates into the courses table for the given
    semester/year if no courses exist yet for that term. Safe to call concurrently —
    duplicate-key errors are caught and the existing data is returned.
    """
    # Check if this term already has courses — if so, nothing to do.
    existing = db.query(models.Course).filter(
        func.lower(models.Course.semester) == semester.lower(),
        models.Course.year == year,
    ).first()
    if existing is not None:
        return db.query(models.Course).filter(
            func.lower(models.Course.semester) == semester.lower(),
            models.Course.year == year,
        ).all()

    templates = db.query(models.CourseTemplate).all()
    if not templates:
        raise HTTPException(
            status_code=404,
            detail="No course templates found. Seed the database first."
        )

    new_courses = [
        models.Course(
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
            core_wem=t.core_wem,
            is_timeless=t.is_timeless,
        )
        for t in templates
    ]

    try:
        db.add_all(new_courses)
        db.commit()
    except IntegrityError:
        # Another concurrent request already inserted — roll back and return what's there.
        db.rollback()

    return db.query(models.Course).filter(
        func.lower(models.Course.semester) == semester.lower(),
        models.Course.year == year,
    ).all()


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

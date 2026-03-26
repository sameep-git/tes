from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from collections import Counter, defaultdict
import logging

from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/insights", tags=["insights"])

logger = logging.getLogger(__name__)

class InsightSummary(BaseModel):
    hotCourse: Optional[Dict[str, Any]] = None
    peakTime: Optional[Dict[str, Any]] = None
    mostAvoidedTime: Optional[Dict[str, Any]] = None
    readiness: Dict[str, int]

class TimeslotInsight(BaseModel):
    id: int
    label: str  # e.g. "MWF 9:00-9:50"
    days: str   # e.g. "MWF"
    startTime: str # e.g. "09:00"
    preferred: int
    avoided: int

class CourseInsight(BaseModel):
    code: str
    name: str
    preferred: int
    avoided: int

class InsightsResponse(BaseModel):
    summary: InsightSummary
    timeslotData: List[TimeslotInsight]
    courseData: List[CourseInsight]

@router.get("/", response_model=InsightsResponse)
def get_insights(
    semester: str,
    year: int,
    db: Session = Depends(get_db)
):
    semester = semester.capitalize() if semester else semester
    # Use .count() instead of loading all objects
    total_active = db.query(models.Professor).filter(models.Professor.active == True).count()
    
    # Get the latest approved preference for each professor
    subquery = db.query(
        models.Preference.professor_id,
        func.max(models.Preference.received_at).label("max_received_at")
    ).filter(
        func.lower(models.Preference.semester) == semester.lower(),
        models.Preference.year == year,
        models.Preference.admin_approved == True
    ).group_by(models.Preference.professor_id).subquery()

    approved_prefs_query = db.query(models.Preference).join(
        subquery,
        (models.Preference.professor_id == subquery.c.professor_id) &
        (models.Preference.received_at == subquery.c.max_received_at)
    ).filter(
        func.lower(models.Preference.semester) == semester.lower(),
        models.Preference.year == year,
        models.Preference.admin_approved == True
    )
    approved_count = approved_prefs_query.count()
    approved_prefs_data = approved_prefs_query.with_entities(models.Preference.parsed_json).yield_per(100)
    
    # Use full "CODE | Name" as the key for courses
    course_pref_counter = Counter()
    course_avoid_counter = Counter()
    
    # Use full timeslot label as the key for timeslots
    ts_pref_counter = Counter()
    ts_avoid_counter = Counter()
    
    all_timeslots = {t.label: t for t in db.query(models.TimeSlot).all()}

    for (parsed_json,) in approved_prefs_data:
        data = parsed_json or {}
        
        # Courses - Now keeping the full "CODE | Name"
        for c in data.get("preferred_courses", []):
            course_pref_counter[c] += 1
            
        for c in data.get("avoid_courses", []):
            course_avoid_counter[c] += 1
            
        # Timeslots - Aggregate by full object label
        for ts_label in data.get("preferred_timeslots", []):
            if ts_label in all_timeslots:
                ts_pref_counter[ts_label] += 1
            
        for ts_label in data.get("avoid_timeslots", []):
            if ts_label in all_timeslots:
                ts_avoid_counter[ts_label] += 1

    # Fetch all courses to build a canonical map
    all_courses = db.query(models.Course).all()
    course_map = {f"{c.code} | {c.name}": c for c in all_courses}
    
    # Build a robust fallback map: code -> list of courses
    code_to_courses = defaultdict(list)
    for c in all_courses:
        code_to_courses[c.code].append(c)
    
    course_insights = []
    all_seen_course_keys = set(course_pref_counter.keys()) | set(course_avoid_counter.keys())
    
    for key in all_seen_course_keys:
        if key in course_map:
            c = course_map[key]
            code = c.code
            name = c.name
        elif key in code_to_courses:
            # If code is ambiguous (multiple courses), use the first one but mark as ambiguous if needed
            # In this context, we'll use the canonical key from the preference if it matches the code
            courses_with_code = code_to_courses[key]
            c = courses_with_code[0]
            code = c.code
            name = c.name if len(courses_with_code) == 1 else f"{c.name} (Ambiguous)"
        else:
            # If it's something weird, try to split it or use as is
            parts = key.split(" | ")
            code = parts[0]
            name = parts[1] if len(parts) > 1 else "Unknown Course"

        course_insights.append(CourseInsight(
            code=code,
            name=name,
            preferred=course_pref_counter[key],
            avoided=course_avoid_counter[key]
        ))
    
    # Sort courses deterministically: preferred desc, then code, then name
    course_insights.sort(key=lambda x: (-x.preferred, x.code, x.name))
    
    # Build Timeslot Data by exact timeslots
    ts_insights = []
    
    # Include all active timeslots even if 0 demand to ensure they show up on charts
    for ts_label, ts in all_timeslots.items():
        if ts.active:
            ts_insights.append(TimeslotInsight(
                id=ts.id,
                label=ts.label,
                days=ts.days,
                startTime=ts.start_time,
                preferred=ts_pref_counter.get(ts_label, 0),
                avoided=ts_avoid_counter.get(ts_label, 0)
            ))
            
    # Sort timeslots sequentially by days, then start_time
    # E.g. M, T, W, R, F, MW, TR, MWF
    # To keep simple for now, sort primarily by startTime so heatmap flows chronologically 
    # and let the frontend do day-sorting if grouped by days.
    ts_insights.sort(key=lambda x: (x.startTime, x.days))
    
    # Summary Highlights
    hot_course = None
    if course_pref_counter:
        top_key, top_count = course_pref_counter.most_common(1)[0]
        parts = top_key.split(" | ")
        display_code = parts[0]
        display_name = parts[1] if len(parts) > 1 else None
        hot_course = {
            "code": display_code, 
            "name": display_name,
            "canonicalKey": top_key,
            "count": top_count
        }
        
    peak_time = None
    if ts_pref_counter:
        top_label, top_count = ts_pref_counter.most_common(1)[0]
        peak_time = {"label": top_label, "count": top_count}
        
    avoided_time = None
    if ts_avoid_counter:
        top_label, top_count = ts_avoid_counter.most_common(1)[0]
        avoided_time = {"label": top_label, "count": top_count}

    return InsightsResponse(
        summary=InsightSummary(
            hotCourse=hot_course,
            peakTime=peak_time,
            mostAvoidedTime=avoided_time,
            readiness={"approved": approved_count, "total": total_active}
        ),
        timeslotData=ts_insights,
        courseData=course_insights
    )

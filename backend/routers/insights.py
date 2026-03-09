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
    label: str  # e.g. "9 AM"
    preferred: int
    avoided: int
    sortKey: int # e.g. 9

class CourseInsight(BaseModel):
    code: str
    name: str
    preferred: int
    avoided: int

class InsightsResponse(BaseModel):
    summary: InsightSummary
    timeslotData: List[TimeslotInsight]
    courseData: List[CourseInsight]

def format_hour_label(hour: int) -> str:
    """Convert hour integer to label like '9 AM' or '12 PM'"""
    if hour == 0:
        return "12 AM"
    if hour == 12:
        return "12 PM"
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    return f"{display_hour} {suffix}"

def get_hour_bucket(start_time_str: str) -> tuple[str, int]:
    """Convert '09:30' to ('9 AM', 9)"""
    try:
        if not start_time_str or ':' not in start_time_str:
            raise ValueError(f"Invalid time format: {start_time_str}")
        hour = int(start_time_str.split(':')[0])
        return format_hour_label(hour), hour
    except (ValueError, IndexError, AttributeError) as e:
        logger.error(f"Error parsing time bucket for '{start_time_str}': {e}")
        return "Unknown", 99

@router.get("/", response_model=InsightsResponse)
def get_insights(
    semester: str,
    year: int,
    db: Session = Depends(get_db)
):
    # Use .count() instead of loading all objects
    total_active = db.query(models.Professor).filter(models.Professor.active == True).count()
    
    # Get the latest approved preference for each professor
    subquery = db.query(
        models.Preference.professor_id,
        func.max(models.Preference.received_at).label("max_received_at")
    ).filter(
        models.Preference.semester == semester,
        models.Preference.year == year,
        models.Preference.admin_approved == True
    ).group_by(models.Preference.professor_id).subquery()

    approved_prefs_query = db.query(models.Preference).join(
        subquery,
        (models.Preference.professor_id == subquery.c.professor_id) &
        (models.Preference.received_at == subquery.c.max_received_at)
    ).filter(
        models.Preference.semester == semester,
        models.Preference.year == year,
        models.Preference.admin_approved == True
    )
    approved_count = approved_prefs_query.count()
    approved_prefs_data = approved_prefs_query.with_entities(models.Preference.parsed_json).yield_per(100)
    
    # Use full "CODE | Name" as the key for courses
    course_pref_counter = Counter()
    course_avoid_counter = Counter()
    
    # Use hour integer (e.g., 9) as the key for timeslots
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
            
        # Timeslots - Aggregate by hour bucket
        for ts_label in data.get("preferred_timeslots", []):
            ts_obj = all_timeslots.get(ts_label)
            if ts_obj:
                _, hour = get_hour_bucket(ts_obj.start_time)
                ts_pref_counter[hour] += 1
            
        for ts_label in data.get("avoid_timeslots", []):
            ts_obj = all_timeslots.get(ts_label)
            if ts_obj:
                _, hour = get_hour_bucket(ts_obj.start_time)
                ts_avoid_counter[hour] += 1

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
    
    # Build Timeslot Data by Hour
    ts_insights = []
    all_seen_hours = set(ts_pref_counter.keys()) | set(ts_avoid_counter.keys())
    
    # Also include hours that exist in active timeslots even if 0 demand
    for ts in all_timeslots.values():
        if ts.active:
            _, hour = get_hour_bucket(ts.start_time)
            all_seen_hours.add(hour)

    for hour in all_seen_hours:
        if hour == 99: continue # Skip unknowns
        
        ts_insights.append(TimeslotInsight(
            label=format_hour_label(hour),
            preferred=ts_pref_counter.get(hour, 0),
            avoided=ts_avoid_counter.get(hour, 0),
            sortKey=hour
        ))
        
    ts_insights.sort(key=lambda x: x.sortKey)
    
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
        top_hour, top_count = ts_pref_counter.most_common(1)[0]
        peak_time = {"label": format_hour_label(top_hour), "count": top_count}
        
    avoided_time = None
    if ts_avoid_counter:
        top_hour, top_count = ts_avoid_counter.most_common(1)[0]
        avoided_time = {"label": format_hour_label(top_hour), "count": top_count}

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

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from collections import Counter

from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/insights", tags=["insights"])

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

def get_hour_bucket(start_time_str: str) -> tuple[str, int]:
    """Convert '09:30' to ('9 AM', 9)"""
    try:
        hour = int(start_time_str.split(':')[0])
        label = f"{hour if hour <= 12 else hour - 12} {'AM' if hour < 12 else 'PM'}"
        # Handle 12 PM (noon) and 12 AM (midnight)
        if hour == 0:
            label = "12 AM"
        elif hour == 12:
            label = "12 PM"
        return label, hour
    except:
        return "Unknown", 99

@router.get("/", response_model=InsightsResponse)
def get_insights(
    semester: str,
    year: int,
    db: Session = Depends(get_db)
):
    active_profs = db.query(models.Professor).filter(models.Professor.active == True).all()
    total_active = len(active_profs)
    
    approved_prefs = db.query(models.Preference).filter(
        models.Preference.semester == semester,
        models.Preference.year == year,
        models.Preference.admin_approved == True
    ).all()
    approved_count = len(approved_prefs)
    
    # Use full "CODE | Name" as the key for courses
    course_pref_counter = Counter()
    course_avoid_counter = Counter()
    
    # Use hour integer (e.g., 9) as the key for timeslots
    ts_pref_counter = Counter()
    ts_avoid_counter = Counter()
    
    all_timeslots = {t.label: t for t in db.query(models.TimeSlot).all()}

    for pref in approved_prefs:
        data = pref.parsed_json or {}
        
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

    # Fetch all courses to build a canonical map of CODE | Name -> Course Object
    all_courses = db.query(models.Course).all()
    course_map = {f"{c.code} | {c.name}": c for c in all_courses}
    # Also build a fallback map just by code in case the JSON only has the code
    fallback_course_map = {c.code: c for c in all_courses}
    
    course_insights = []
    all_seen_course_keys = set(course_pref_counter.keys()) | set(course_avoid_counter.keys())
    
    for key in all_seen_course_keys:
        if key in course_map:
            c = course_map[key]
            code = c.code
            name = c.name
        elif key in fallback_course_map:
            # Fallback if preference just had "ECON 10223"
            c = fallback_course_map[key]
            code = c.code
            name = c.name
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
        
        label = f"{hour if hour <= 12 else hour - 12} {'AM' if hour < 12 else 'PM'}"
        if hour == 0: label = "12 AM"
        elif hour == 12: label = "12 PM"
            
        ts_insights.append(TimeslotInsight(
            label=label,
            preferred=ts_pref_counter.get(hour, 0),
            avoided=ts_avoid_counter.get(hour, 0),
            sortKey=hour
        ))
        
    ts_insights.sort(key=lambda x: x.sortKey)
    
    # Summary Highlights
    hot_course = None
    if course_pref_counter:
        top_key, top_count = course_pref_counter.most_common(1)[0]
        # Try to format it nicely for the summary card
        parts = top_key.split(" | ")
        display_code = parts[0]
        hot_course = {"code": display_code, "count": top_count}
        
    peak_time = None
    if ts_pref_counter:
        top_hour, top_count = ts_pref_counter.most_common(1)[0]
        label = f"{top_hour if top_hour <= 12 else top_hour - 12} {'AM' if top_hour < 12 else 'PM'}"
        if top_hour == 0: label = "12 AM"
        elif top_hour == 12: label = "12 PM"
        peak_time = {"label": label, "count": top_count}
        
    avoided_time = None
    if ts_avoid_counter:
        top_hour, top_count = ts_avoid_counter.most_common(1)[0]
        label = f"{top_hour if top_hour <= 12 else top_hour - 12} {'AM' if top_hour < 12 else 'PM'}"
        if top_hour == 0: label = "12 AM"
        elif top_hour == 12: label = "12 PM"
        avoided_time = {"label": label, "count": top_count}

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

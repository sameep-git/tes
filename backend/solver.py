"""
Solver orchestrator.

gather_solver_input()  — queries the DB and builds a JSON-serializable payload
run_solver()           — calls gather_solver_input(), invokes Lambda, writes results to DB
"""
import json
import os
from typing import Any, Dict

import boto3
from botocore.config import Config

from .database import SessionLocal
from .models import Professor, Course, TimeSlot, Schedule, Section, Preference, Room, Constraint


# ── Lambda client (created once at module import time) ──────────────────────
_lambda_client = None


def _get_lambda_client():
    """Lazily build the boto3 Lambda client so unit tests can patch it easily."""
    global _lambda_client
    if _lambda_client is None:
        # Increase read_timeout so boto3 doesn't drop the connection
        # before the 10-minute Lambda function finishes.
        boto_config = Config(
            read_timeout=610,
            connect_timeout=10,
            retries={'max_attempts': 0}
        )
        _lambda_client = boto3.client(
            "lambda",
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
            config=boto_config
        )
    return _lambda_client


# ── Data gathering ───────────────────────────────────────────────────────────

def gather_solver_input(semester: str, year: int) -> Dict[str, Any]:
    """
    Query the DB and return a JSON-serializable dict that can be sent to Lambda.
    This is the only function in solver.py that touches the database.
    """
    db = SessionLocal()
    try:
        professors = db.query(Professor).filter(Professor.active == True).all()
        courses = db.query(Course).filter(Course.semester == semester, Course.year == year).all()
        timeslots = db.query(TimeSlot).filter(TimeSlot.active == True).all()
        rooms = db.query(Room).all()

        if not professors or not courses or not timeslots or not rooms:
            return {}  # caller checks for empty dict

        # Build preferences dict keyed by str(prof_id) for JSON compatibility
        preferences = {}
        for p in professors:
            pref = db.query(Preference).filter(
                Preference.professor_id == p.id,
                Preference.semester == semester,
                Preference.year == year,
            ).first()
            preferences[str(p.id)] = pref.parsed_json if (pref and pref.parsed_json) else {}

        # Constraint configs
        constraints: Dict[str, Any] = {}

        prime_row = db.query(Constraint).filter(
            Constraint.name == "prime_time", Constraint.active == True
        ).first()
        if prime_row and prime_row.value_json:
            constraints["prime_time"] = prime_row.value_json

        blocked_row = db.query(Constraint).filter(
            Constraint.name == "blocked_timeslots", Constraint.active == True
        ).first()
        if blocked_row and blocked_row.value_json:
            constraints["blocked_timeslots"] = blocked_row.value_json

        return {
            "semester": semester,
            "year": year,
            "professors": [
                {
                    "id": p.id,
                    "name": p.name,
                    "fall_count": p.fall_count,
                    "spring_count": p.spring_count,
                }
                for p in professors
            ],
            "courses": [
                {
                    "id": c.id,
                    "code": c.code,
                    "name": c.name,
                    "level": c.level,
                    "capacity": c.capacity,
                    "min_sections": c.min_sections,
                    "max_sections": c.max_sections,
                    "is_timeless": c.is_timeless,
                }
                for c in courses
                if not c.is_timeless  # timeless courses are pre-assigned; skip Lambda
            ],
            "timeslots": [
                {
                    "id": t.id,
                    "label": t.label,
                    "days": t.days,
                    "start_time": t.start_time,
                    "end_time": t.end_time,
                    "max_classes": t.max_classes,
                }
                for t in timeslots
            ],
            "rooms": [{"id": r.id, "capacity": r.capacity} for r in rooms],
            "preferences": preferences,
            "constraints": constraints,
        }
    finally:
        db.close()


# ── Pre-assignment: timeless courses ────────────────────────────────────────

def pre_assign_timeless_courses(
    semester: str, year: int, schedule_id: int, preferences: Dict[str, Any]
) -> int:
    """
    Before the solver runs, scan all approved preferences for course_assignments
    that reference timeless courses (is_timeless=True). Create a Section for each
    such assignment directly, without going through Lambda.

    Returns the number of timeless sections created.
    """
    db = SessionLocal()
    try:
        # Build a lookup: "CODE | name" -> Course object (timeless only)
        timeless_courses = db.query(Course).filter(
            Course.semester == semester,
            Course.year == year,
            Course.is_timeless == True,
        ).all()
        if not timeless_courses:
            return 0

        timeless_map: Dict[str, Course] = {
            f"{c.code} | {c.name}": c for c in timeless_courses
        }
        # Also allow bare code lookup (in case AI drops the name part)
        timeless_code_map: Dict[str, Course] = {
            c.code: c for c in timeless_courses
        }

        sections_created = 0
        for prof_id_str, pref in preferences.items():
            prof_id = int(prof_id_str)
            assignments = pref.get("course_assignments", [])
            for entry in assignments:
                course_key = entry.get("course", "")
                # Try full key first, then bare code
                course = timeless_map.get(course_key) or timeless_code_map.get(course_key)
                if not course:
                    continue  # not a timeless course — solver handles it

                new_sec = Section(
                    course_id=course.id,
                    professor_id=prof_id,
                    timeslot_id=None,   # no meeting time
                    room_id=None,       # no room needed
                    schedule_id=schedule_id,
                    status="Assigned",
                )
                db.add(new_sec)
                sections_created += 1

        db.commit()
        return sections_created
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Orchestrator ─────────────────────────────────────────────────────────────

def run_solver(semester: str, year: int) -> Dict[str, Any]:
    """
    1. Gather input data from DB
    2. Invoke the Lambda function with the payload
    3. Parse the result and write Schedule + Section rows to DB
    """
    # Step 1: Gather data
    payload = gather_solver_input(semester, year)
    if not payload:
        return {"status": "error", "message": "Missing basic data (professors, courses, timeslots, or rooms)."}

    # Step 2: Invoke Lambda
    function_name = os.environ.get("SOLVER_LAMBDA_FUNCTION", "tes-solver")
    try:
        response = _get_lambda_client().invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",  # synchronous — wait for the result
            Payload=json.dumps(payload).encode(),
        )
    except Exception as e:
        return {"status": "error", "message": f"Failed to invoke Lambda function '{function_name}': {e}"}

    # Parse Lambda response
    raw = response["Payload"].read()
    try:
        result: Dict[str, Any] = json.loads(raw)
    except Exception:
        return {"status": "error", "message": f"Lambda returned non-JSON response: {raw[:500]}"}

    # Lambda itself can return a {"errorMessage": ...} on unhandled exceptions
    if "errorMessage" in result:
        return {"status": "error", "message": f"Lambda unhandled error: {result['errorMessage']}"}

    # Step 3: Write to DB if solver succeeded
    if result.get("status") == "success":
        db = SessionLocal()
        try:
            new_schedule = Schedule(
                semester=semester,
                year=year,
                status="Draft",
                solver_log=(
                    f"Status: {result.get('solver_status')}\n"
                    f"Score: {result.get('score')}\n"
                    f"Time: {result.get('wall_time')}s"
                ),
            )
            db.add(new_schedule)
            db.commit()

            # Step 3a: Pre-assign timeless courses from professor preferences
            timeless_count = pre_assign_timeless_courses(
                semester, year, new_schedule.id, payload.get("preferences", {})
            )

            # Step 3b: Create solver-assigned sections
            sections_created = 0
            for assignment in result.get("assignments", []):
                new_sec = Section(
                    course_id=assignment["course_id"],
                    professor_id=assignment["professor_id"],
                    timeslot_id=assignment["timeslot_id"],
                    room_id=assignment["room_id"],
                    schedule_id=new_schedule.id,
                    status="Assigned",
                )
                db.add(new_sec)
                sections_created += 1

            db.commit()

            return {
                "status": "success",
                "solution_type": result.get("solver_status"),
                "schedule_id": new_schedule.id,
                "sections_created": sections_created + timeless_count,
                "timeless_sections": timeless_count,
                "score": result.get("score"),
            }
        except Exception as e:
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()

    # Pass through infeasible / error results unchanged
    return result

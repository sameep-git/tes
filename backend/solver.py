"""
Solver orchestrator.

gather_solver_input()  — queries the DB and builds a JSON-serializable payload
run_solver()           — calls gather_solver_input(), invokes Lambda, writes results to DB
"""
import json
import os
from typing import Any, Dict

import boto3

from .database import SessionLocal
from .models import Professor, Course, TimeSlot, Schedule, Section, Preference, Room, Constraint


# ── Lambda client (created once at module import time) ──────────────────────
_lambda_client = None


def _get_lambda_client():
    """Lazily build the boto3 Lambda client so unit tests can patch it easily."""
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client(
            "lambda",
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
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
                }
                for c in courses
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
                "sections_created": sections_created,
                "score": result.get("score"),
            }
        except Exception as e:
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()

    # Pass through infeasible / error results unchanged
    return result

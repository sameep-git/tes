import json
from fastmcp import FastMCP
import sys
import os

# Add the parent directory to sys.path to import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal
from backend.models import Professor, Schedule, Constraint, Preference, Course
from backend.email import send_preference_email, poll_unread_replies
from backend.ai import extract_preferences_from_email

# Initialize FastMCP server
mcp = FastMCP("TES")

@mcp.tool()
def get_courses() -> str:
    """Retrieve all available courses and their core requirements."""
    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        courses_data = []
        for c in courses:
            courses_data.append({
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "credits": c.credits,
                "level": c.level,
                "min_sections": c.min_sections,
                "max_sections": c.max_sections,
                "requires_lab": c.requires_lab,
                "core_ssc": c.core_ssc,
                "core_ht": c.core_ht,
                "core_ga": c.core_ga,
                "core_wem": c.core_wem
            })
        return json.dumps(courses_data)
    finally:
        db.close()

@mcp.tool()
def get_professor(prof_id: int) -> str:
    """Retrieve professor details by their ID."""
    db = SessionLocal()

    try:
        prof = db.query(Professor).filter(Professor.id == prof_id).first()
        if not prof:
            return json.dumps({"error": f"Professor with ID {prof_id} not found."})
        
        prof_data = {
            "id": prof.id,
            "name": prof.name,
            "email": prof.email,
            "office": prof.office,
            "rank": prof.rank,
            "max_sections": prof.max_sections,
            "active": prof.active
        }
        return json.dumps(prof_data)
    finally:
        db.close()

@mcp.tool()
def get_schedule(year: int, semester: str) -> str:
    """Retrieve schedule details for a given semester and year."""
    db = SessionLocal()

    try:
        schedule = db.query(Schedule).filter(Schedule.year == year, Schedule.semester == semester).first()
        if not schedule:
            return json.dumps({"error": f"Schedule for {semester} {year} not found."})
        
        schedule_data = {
            "id": schedule.id,
            "semester": schedule.semester,
            "year": schedule.year,
            "status": schedule.status,
            "solver_log": schedule.solver_log,
            "finalized_at": schedule.finalized_at.isoformat() if schedule.finalized_at is not None else None,
            "excel_path": schedule.excel_path,
            "sections": [section.id for section in schedule.sections]
        }
        return json.dumps(schedule_data)
    finally:
        db.close()

@mcp.tool()
def get_unreplied_professors(year: int, semester: str) -> str:
    """Retrieve professors who have not replied yet for the given year and semester."""
    db = SessionLocal()
    
    try:
        # Find professor IDs who DO have a preference record for this semester/year
        subquery = db.query(Preference.professor_id).filter(
            Preference.year == year, 
            Preference.semester == semester
        ).scalar_subquery()
        
        # Query active professors whose ID is NOT in the subquery
        unreplied_professors = db.query(Professor).filter(
            Professor.active == True,
            Professor.id.notin_(subquery)
        ).all()

        if not unreplied_professors:
            return json.dumps({"message": "All active professors have replied for this semester."})
        
        unreplied_professors_data = []
        for prof in unreplied_professors:
            unreplied_professors_data.append({
                "id": prof.id,
                "name": prof.name,
                "email": prof.email,
                "office": prof.office,
                "rank": prof.rank,
                "max_sections": prof.max_sections,
                "active": prof.active
            })
        return json.dumps(unreplied_professors_data)
    finally:
        db.close()

@mcp.tool()
def get_constraints() -> str:
    """
    Retrieve all active scheduling constraints (both hard and soft) 
    from the database so the solver can be informed of the rules.
    """
    db = SessionLocal()

    try:
        constraints = db.query(Constraint).filter(Constraint.active == True).all()
        if not constraints:
            return json.dumps({"error": "No active constraints found."})
        
        constraints_data = []
        for constraint in constraints:
            constraints_data.append({
                "id": constraint.id,
                "type": constraint.type,
                "name": constraint.name,
                "value_json": constraint.value_json
            })
        return json.dumps(constraints_data)
    finally:
        db.close()


@mcp.tool()
def trigger_send_preference_email(prof_id: int, semester: str, year: int) -> str:
    """Send an email to a specific professor asking for their teaching preferences."""
    result = send_preference_email(prof_id, semester, year)
    return json.dumps(result)

@mcp.tool()
def trigger_poll_unread_replies() -> str:
    """Poll the system email inbox for any unread preference replies and save them to the database."""
    replies = poll_unread_replies()
    return json.dumps({"processed_count": len(replies), "replies": replies})

@mcp.tool()
def extract_and_save_preference_json(pref_id: int) -> str:
    """
    Takes an existing Preference record (which must have raw_email text),
    runs the AI extraction on it to generate structured JSON,
    and saves the JSON back to the database.
    """
    db = SessionLocal()
    try:
        pref = db.query(Preference).filter(Preference.id == pref_id).first()
        if not pref:
            return json.dumps({"error": f"Preference record {pref_id} not found."})
        
        raw_email = pref.raw_email
        if raw_email is None:
            return json.dumps({"error": f"Preference record {pref_id} does not have raw_email text."})
        raw_email_str = str(raw_email).strip()
        if not raw_email_str:
            return json.dumps({"error": f"Preference record {pref_id} does not have raw_email text."})

        # Run the AI extraction
        parsed_obj = extract_preferences_from_email(raw_email_str)
        
        # Save it to the database
        pref.parsed_json = parsed_obj.model_dump()  # type: ignore[assignment]
        pref.confidence = parsed_obj.confidence_score  # type: ignore[assignment]
        db.commit()

        return json.dumps({
            "status": "success",
            "preference_id": pref.id,
            "confidence_score": pref.confidence,
            "parsed_json": pref.parsed_json
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": f"Extraction failed: {str(e)}"})
    finally:
        db.close()


if __name__ == "__main__":
    # Standard MCP run execution using stdio by default
    mcp.run()
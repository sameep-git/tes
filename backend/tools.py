"""
Centralized tool registry for the TES AI agent.

Every function here returns a JSON string so Gemini can consume it directly.
These functions are imported by backend/routers/chat.py and passed to Gemini
as callable tools.
"""

import json
from datetime import datetime
from typing import Optional

from .database import SessionLocal
from .models import Professor, Course, TimeSlot, Preference, Section
from .email import poll_unread_replies, send_preference_email
from .ai import extract_preferences_from_email
from .solver import run_solver


# =========================================================================
# Existing tools (migrated from chat.py & mcp_server/server.py)
# =========================================================================

def get_professor(prof_id: int) -> str:
    """Retrieve professor details by their ID."""
    db = SessionLocal()
    try:
        prof = db.query(Professor).filter(Professor.id == prof_id).first()
        if not prof:
            return json.dumps({"error": f"Professor with ID {prof_id} not found."})
        return json.dumps({
            "id": prof.id, "name": prof.name, "email": prof.email,
            "office": prof.office, "rank": prof.rank,
            "max_sections": prof.max_sections, "active": prof.active
        })
    finally:
        db.close()


def get_courses() -> str:
    """Retrieve all available courses and their core requirements."""
    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        return json.dumps([{
            "id": c.id, "code": c.code, "name": c.name, "credits": c.credits,
            "level": c.level, "min_sections": c.min_sections,
            "max_sections": c.max_sections, "requires_lab": c.requires_lab,
            "core_ssc": c.core_ssc, "core_ht": c.core_ht,
            "core_ga": c.core_ga, "core_wem": c.core_wem
        } for c in courses])
    finally:
        db.close()


def get_unreplied_professors(year: int, semester: str) -> str:
    """Retrieve professors who have not replied yet for the given year and semester."""
    db = SessionLocal()
    try:
        subquery = db.query(Preference.professor_id).filter(
            Preference.year == year, Preference.semester == semester
        ).scalar_subquery()

        unreplied = db.query(Professor).filter(
            Professor.active == True,
            Professor.id.notin_(subquery)
        ).all()

        if not unreplied:
            return json.dumps({"message": "All active professors have replied for this semester."})

        return json.dumps([{
            "id": p.id, "name": p.name, "email": p.email, "active": p.active
        } for p in unreplied])
    finally:
        db.close()


# Confidence threshold for auto-approval (configurable)
AUTO_APPROVE_CONFIDENCE_THRESHOLD = 0.85


def trigger_poll_unread_replies(server_mode: bool = False) -> str:
    """
    Poll the system email inbox for any unread preference replies and save them to the database.
    Pipeline:
      1. Poll Gmail for new replies
      2. Auto-extract parsed_json via AI for every new preference
      3. Auto-approve preferences where confidence >= 0.85, on_leave=False, no admin notes
         (lower-confidence or flagged prefs stay pending for human review)
    """
    replies = poll_unread_replies(server_mode=server_mode)

    auto_extracted = []
    auto_approved = []
    needs_review = []

    for reply in replies:
        if "error" in reply or "professor_id" not in reply:
            continue

        db = SessionLocal()
        try:
            pref = db.query(Preference).filter(
                Preference.professor_id == reply["professor_id"],
                Preference.semester == reply["semester"],
                Preference.year == reply["year"],
            ).first()
            if not pref:
                continue

            # Step 2: Auto-extract
            extraction_result_str = extract_and_save_preference_json(pref.id)
            auto_extracted.append({"preference_id": pref.id, "extraction": extraction_result_str})

            # Reload to get freshly parsed data
            db.refresh(pref)
            parsed = pref.parsed_json or {}
            confidence = pref.confidence or 0.0
            on_leave = parsed.get("on_leave", False)
            notes = parsed.get("notes_for_admin", None)

            # Step 3: Auto-approve if high-confidence and clean
            if confidence >= AUTO_APPROVE_CONFIDENCE_THRESHOLD and not on_leave and not notes:
                pref.admin_approved = True
                db.commit()
                prof = db.query(Professor).filter(Professor.id == pref.professor_id).first()
                auto_approved.append({
                    "preference_id": pref.id,
                    "professor_name": prof.name if prof else f"Prof #{pref.professor_id}",
                    "confidence": confidence,
                })
            else:
                reason = []
                if confidence < AUTO_APPROVE_CONFIDENCE_THRESHOLD:
                    reason.append(f"low confidence ({round(confidence * 100)}%)")
                if on_leave:
                    reason.append("on_leave flag set")
                if notes:
                    reason.append("has admin notes")
                prof = db.query(Professor).filter(Professor.id == pref.professor_id).first()
                needs_review.append({
                    "preference_id": pref.id,
                    "professor_name": prof.name if prof else f"Prof #{pref.professor_id}",
                    "reason": ", ".join(reason),
                })
        finally:
            db.close()

    return json.dumps({
        "processed_count": len(replies),
        "auto_approved_count": len(auto_approved),
        "needs_review_count": len(needs_review),
        "auto_approved": auto_approved,
        "needs_review": needs_review,
    })


def trigger_send_preference_email(prof_id: int, semester: str, year: int) -> str:
    """
    Send a preference collection email to a specific professor.
    The email asks them to reply with their teaching preferences for the given semester.
    """
    result = send_preference_email(prof_id, semester, year)
    return json.dumps(result)


def trigger_send_all_preference_emails(semester: str, year: int) -> str:
    """
    Send preference collection emails to ALL active professors who have not yet
    submitted preferences for the given semester and year.
    """
    db = SessionLocal()
    try:
        subquery = db.query(Preference.professor_id).filter(
            Preference.year == year, Preference.semester == semester
        ).scalar_subquery()

        unreplied = db.query(Professor).filter(
            Professor.active == True,
            Professor.id.notin_(subquery)
        ).all()

        if not unreplied:
            return json.dumps({"message": "All active professors already have preference records for this semester. No emails sent."})

        results = []
        for prof in unreplied:
            result = send_preference_email(prof.id, semester, year)
            results.append({"professor_id": prof.id, "name": prof.name, "result": result})

        sent_count = sum(1 for r in results if "error" not in r["result"])
        return json.dumps({
            "sent_count": sent_count,
            "total_unreplied": len(unreplied),
            "results": results
        })
    finally:
        db.close()


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
        if not raw_email or not str(raw_email).strip():
            return json.dumps({"error": f"Preference record {pref_id} does not have raw_email text."})

        parsed_obj = extract_preferences_from_email(str(raw_email).strip())

        pref.parsed_json = parsed_obj.model_dump()
        pref.confidence = parsed_obj.confidence_score
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


def get_preference(pref_id: int) -> str:
    """
    Retrieve the full preference record for a given preference ID, including
    the professor's name, raw email text, parsed JSON, confidence score,
    and approval status.
    """
    db = SessionLocal()
    try:
        pref = db.query(Preference).filter(Preference.id == pref_id).first()
        if not pref:
            return json.dumps({"error": f"Preference record {pref_id} not found."})

        prof = db.query(Professor).filter(Professor.id == pref.professor_id).first()
        return json.dumps({
            "id": pref.id,
            "professor_id": pref.professor_id,
            "professor_name": prof.name if prof else f"Prof #{pref.professor_id}",
            "semester": pref.semester,
            "year": pref.year,
            "raw_email": pref.raw_email,
            "parsed_json": pref.parsed_json,
            "confidence": pref.confidence,
            "admin_approved": pref.admin_approved,
            "received_at": pref.received_at.isoformat() if pref.received_at else None,
        })
    finally:
        db.close()


def get_professor_preference(prof_id: int, semester: str, year: int) -> str:
    """
    Retrieve the preference record for a specific professor and semester.
    Use this when you know the professor ID but not the preference ID.
    """
    db = SessionLocal()
    try:
        pref = db.query(Preference).filter(
            Preference.professor_id == prof_id,
            Preference.semester == semester,
            Preference.year == year
        ).first()
        if not pref:
            return json.dumps({
                "error": f"No preference found for professor {prof_id} for {semester} {year}."
            })

        prof = db.query(Professor).filter(Professor.id == prof_id).first()
        return json.dumps({
            "id": pref.id,
            "professor_id": pref.professor_id,
            "professor_name": prof.name if prof else f"Prof #{prof_id}",
            "semester": pref.semester,
            "year": pref.year,
            "raw_email": pref.raw_email,
            "parsed_json": pref.parsed_json,
            "confidence": pref.confidence,
            "admin_approved": pref.admin_approved,
            "received_at": pref.received_at.isoformat() if pref.received_at else None,
        })
    finally:
        db.close()


def trigger_solver(semester: str, year: int) -> str:
    """Run the Constraint Solver to generate a schedule for the given semester and year."""
    result = run_solver(semester, year)
    return json.dumps(result)


# =========================================================================
# Professor CRUD tools
# =========================================================================

def list_professors() -> str:
    """Retrieve all professors in the system (both active and inactive)."""
    db = SessionLocal()
    try:
        profs = db.query(Professor).all()
        return json.dumps([{
            "id": p.id, "name": p.name, "email": p.email,
            "office": p.office, "rank": p.rank,
            "max_sections": p.max_sections, "active": p.active
        } for p in profs])
    finally:
        db.close()


def create_professor(
    name: str,
    email: str,
    rank: str,
    office: Optional[str] = None,
    max_sections: int = 3
) -> str:
    """Create a new professor in the system."""
    db = SessionLocal()
    try:
        existing = db.query(Professor).filter(Professor.email == email).first()
        if existing:
            return json.dumps({"error": f"A professor with email {email} already exists (ID {existing.id})."})

        prof = Professor(
            name=name, email=email, rank=rank,
            office=office, max_sections=max_sections, active=True
        )
        db.add(prof)
        db.commit()
        db.refresh(prof)
        return json.dumps({
            "status": "success", "id": prof.id, "name": prof.name,
            "email": prof.email, "rank": prof.rank
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


def update_professor(
    prof_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    rank: Optional[str] = None,
    office: Optional[str] = None,
    max_sections: Optional[int] = None,
    active: Optional[bool] = None
) -> str:
    """Update editable fields on a professor. Only provided fields are changed."""
    db = SessionLocal()
    try:
        prof = db.query(Professor).filter(Professor.id == prof_id).first()
        if not prof:
            return json.dumps({"error": f"Professor with ID {prof_id} not found."})

        if name is not None:
            prof.name = name
        if email is not None:
            prof.email = email
        if rank is not None:
            prof.rank = rank
        if office is not None:
            prof.office = office
        if max_sections is not None:
            prof.max_sections = max_sections
        if active is not None:
            prof.active = active

        db.commit()
        db.refresh(prof)
        return json.dumps({
            "status": "success", "id": prof.id, "name": prof.name,
            "email": prof.email, "rank": prof.rank, "active": prof.active
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


def deactivate_professor(prof_id: int) -> str:
    """Soft-delete a professor by setting active = False. Preserves historical data."""
    db = SessionLocal()
    try:
        prof = db.query(Professor).filter(Professor.id == prof_id).first()
        if not prof:
            return json.dumps({"error": f"Professor with ID {prof_id} not found."})
        if not prof.active:
            return json.dumps({"message": f"Professor '{prof.name}' is already inactive."})

        prof.active = False
        db.commit()
        return json.dumps({"status": "success", "message": f"Professor '{prof.name}' has been deactivated."})
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


# =========================================================================
# Course CRUD tools
# =========================================================================

def create_course(
    code: str,
    name: str,
    level: int,
    credits: int = 3,
    min_sections: int = 1,
    max_sections: int = 5,
    requires_lab: bool = False,
    core_ssc: bool = False,
    core_ht: bool = False,
    core_ga: bool = False,
    core_wem: bool = False
) -> str:
    """Create a new course in the system."""
    db = SessionLocal()
    try:
        existing = db.query(Course).filter(Course.code == code).first()
        if existing:
            return json.dumps({"error": f"A course with code {code} already exists (ID {existing.id})."})

        course = Course(
            code=code, name=name, level=level, credits=credits,
            min_sections=min_sections, max_sections=max_sections,
            requires_lab=requires_lab, core_ssc=core_ssc,
            core_ht=core_ht, core_ga=core_ga, core_wem=core_wem
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        return json.dumps({
            "status": "success", "id": course.id,
            "code": course.code, "name": course.name
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


def update_course(
    course_id: int,
    code: Optional[str] = None,
    name: Optional[str] = None,
    level: Optional[int] = None,
    credits: Optional[int] = None,
    min_sections: Optional[int] = None,
    max_sections: Optional[int] = None,
    requires_lab: Optional[bool] = None,
    core_ssc: Optional[bool] = None,
    core_ht: Optional[bool] = None,
    core_ga: Optional[bool] = None,
    core_wem: Optional[bool] = None
) -> str:
    """Update editable fields on a course. Only provided fields are changed."""
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return json.dumps({"error": f"Course with ID {course_id} not found."})

        if code is not None:
            course.code = code
        if name is not None:
            course.name = name
        if level is not None:
            course.level = level
        if credits is not None:
            course.credits = credits
        if min_sections is not None:
            course.min_sections = min_sections
        if max_sections is not None:
            course.max_sections = max_sections
        if requires_lab is not None:
            course.requires_lab = requires_lab
        if core_ssc is not None:
            course.core_ssc = core_ssc
        if core_ht is not None:
            course.core_ht = core_ht
        if core_ga is not None:
            course.core_ga = core_ga
        if core_wem is not None:
            course.core_wem = core_wem

        db.commit()
        db.refresh(course)
        return json.dumps({
            "status": "success", "id": course.id,
            "code": course.code, "name": course.name
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


def delete_course(course_id: int) -> str:
    """Delete a course. Fails if any sections reference this course."""
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return json.dumps({"error": f"Course with ID {course_id} not found."})

        section_count = db.query(Section).filter(Section.course_id == course_id).count()
        if section_count > 0:
            return json.dumps({
                "error": f"Cannot delete course '{course.code}' — it has {section_count} section(s) referencing it. "
                         "Remove or reassign those sections first."
            })

        db.delete(course)
        db.commit()
        return json.dumps({"status": "success", "message": f"Course '{course.code}' has been deleted."})
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


# =========================================================================
# Guardrail tools
# =========================================================================

def run_preflight_checks(semester: str, year: int) -> str:
    """
    Run pre-solver validation checks. Returns a list of blockers that must
    be resolved before the solver can run.

    Checks:
      1. Capacity: sum(prof.max_sections) >= sum(course.min_sections)
      2. Missing profs: any active professors without a preference record
      3. Unapproved prefs: any preference records with admin_approved = False
    """
    db = SessionLocal()
    try:
        blockers = []

        # 1. Capacity check
        profs = db.query(Professor).filter(Professor.active == True).all()
        courses = db.query(Course).all()

        total_capacity = sum(p.max_sections for p in profs)
        total_demand = sum(c.min_sections for c in courses)

        if total_capacity < total_demand:
            blockers.append({
                "type": "capacity",
                "message": f"Insufficient capacity: {len(profs)} active professors can teach "
                           f"{total_capacity} sections total, but {len(courses)} courses require "
                           f"at least {total_demand} sections."
            })

        # 2. Missing professors (active profs with no preference for this term)
        subquery = db.query(Preference.professor_id).filter(
            Preference.year == year, Preference.semester == semester
        ).scalar_subquery()

        missing = db.query(Professor).filter(
            Professor.active == True,
            Professor.id.notin_(subquery)
        ).all()

        if missing:
            names = [p.name for p in missing]
            blockers.append({
                "type": "missing_preferences",
                "message": f"{len(missing)} active professor(s) have not submitted preferences: "
                           f"{', '.join(names)}",
                "professor_ids": [p.id for p in missing]
            })

        # 3. Unapproved preferences
        unapproved = db.query(Preference).filter(
            Preference.semester == semester,
            Preference.year == year,
            Preference.admin_approved == False
        ).all()

        if unapproved:
            prof_ids = [u.professor_id for u in unapproved]
            prof_names = []
            for pid in prof_ids:
                p = db.query(Professor).filter(Professor.id == pid).first()
                prof_names.append(p.name if p else f"Prof #{pid}")

            blockers.append({
                "type": "unapproved_preferences",
                "message": f"{len(unapproved)} preference(s) pending admin approval: "
                           f"{', '.join(prof_names)}",
                "preference_ids": [u.id for u in unapproved]
            })

        return json.dumps({
            "ready": len(blockers) == 0,
            "blockers": blockers,
            "summary": {
                "active_professors": len(profs),
                "total_courses": len(courses),
                "total_capacity": total_capacity,
                "total_demand": total_demand
            }
        })
    finally:
        db.close()


def create_manual_preference(
    prof_id: int,
    instructions: str,
    semester: str,
    year: int
) -> str:
    """
    Create a preference record for a professor from natural-language instructions
    typed in the chat (e.g., "mornings only, prefers Micro"). Uses the AI
    extraction pipeline to generate structured JSON.
    """
    db = SessionLocal()
    try:
        prof = db.query(Professor).filter(Professor.id == prof_id).first()
        if not prof:
            return json.dumps({"error": f"Professor with ID {prof_id} not found."})

        # Check if preference already exists
        existing = db.query(Preference).filter(
            Preference.professor_id == prof_id,
            Preference.semester == semester,
            Preference.year == year
        ).first()
        if existing:
            return json.dumps({
                "error": f"Professor '{prof.name}' already has a preference record "
                         f"for {semester} {year} (ID {existing.id}). "
                         "Use extract_and_save_preference_json to re-extract, "
                         "or approve_preference to approve it."
            })

        # Use the AI to parse the natural language instructions
        parsed_obj = extract_preferences_from_email(instructions)

        pref = Preference(
            professor_id=prof_id,
            semester=semester,
            year=year,
            raw_email=f"[Manual entry via chat] {instructions}",
            parsed_json=parsed_obj.model_dump(),
            confidence=parsed_obj.confidence_score,
            admin_approved=False,
            received_at=datetime.utcnow()
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

        return json.dumps({
            "status": "success",
            "preference_id": pref.id,
            "professor_name": prof.name,
            "confidence_score": pref.confidence,
            "parsed_json": pref.parsed_json,
            "note": "Preference created but NOT approved. Use approve_preference to approve it."
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": f"Failed to create preference: {str(e)}"})
    finally:
        db.close()


def approve_preference(pref_id: int) -> str:
    """
    Approve a preference record, marking it as admin_approved = True.
    Automatically runs preflight checks after approval so you know immediately
    whether the system is now ready to run the solver.
    """
    db = SessionLocal()
    # Capture these before db.close() — after close() the ORM instance is
    # detached and accessing its attributes raises DetachedInstanceError.
    pref_semester: str | None = None
    pref_year: int | None = None
    prof_name: str = f"Prof #{pref_id}"

    try:
        pref = db.query(Preference).filter(Preference.id == pref_id).first()
        if not pref:
            return json.dumps({"error": f"Preference record {pref_id} not found."})

        if pref.admin_approved:
            return json.dumps({"message": f"Preference {pref_id} is already approved."})

        pref.admin_approved = True
        db.commit()

        # Capture scalar values before the session is closed
        pref_semester = pref.semester
        pref_year = pref.year

        prof = db.query(Professor).filter(Professor.id == pref.professor_id).first()
        prof_name = prof.name if prof else f"Prof #{pref.professor_id}"
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()

    # Auto-run preflight so the AI can tell the user if they're ready to run the solver
    preflight_result = run_preflight_checks(semester=pref_semester, year=pref_year)

    return json.dumps({
        "status": "success",
        "preference_id": pref_id,
        "professor_name": prof_name,
        "message": "Preference approved.",
        "preflight": json.loads(preflight_result),
    })


# =========================================================================
# Schedule management tools
# =========================================================================

def list_schedules(semester: Optional[str] = None, year: Optional[int] = None) -> str:
    """
    List all generated schedules. Optionally filter by semester and/or year.
    Returns schedule IDs, status, section count, and finalized date.
    Use this to find a schedule ID before calling delete_schedule, finalize_schedule, or get_schedule_stats.
    """
    from .models import Schedule
    db = SessionLocal()
    try:
        query = db.query(Schedule)
        if semester:
            query = query.filter(Schedule.semester == semester)
        if year:
            query = query.filter(Schedule.year == year)
        schedules = query.order_by(Schedule.year.desc(), Schedule.semester).all()

        if not schedules:
            filter_str = f" for {semester} {year}" if semester or year else ""
            return json.dumps({"message": f"No schedules found{filter_str}."})

        return json.dumps([{
            "id": s.id,
            "semester": s.semester,
            "year": s.year,
            "status": s.status,
            "section_count": db.query(Section).filter(Section.schedule_id == s.id).count(),
            "finalized_at": s.finalized_at.isoformat() if s.finalized_at else None,
        } for s in schedules])
    finally:
        db.close()

def finalize_schedule(schedule_id: int) -> str:
    """Mark a Draft schedule as Finalized. This is the official published schedule for the term."""
    from .models import Schedule
    db = SessionLocal()
    try:
        sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not sched:
            return json.dumps({"error": f"Schedule {schedule_id} not found."})
        if sched.status == "Finalized":
            return json.dumps({"message": f"Schedule {schedule_id} is already finalized."})
        sched.status = "Finalized"
        sched.finalized_at = datetime.utcnow()
        db.commit()
        return json.dumps({
            "status": "success",
            "schedule_id": schedule_id,
            "semester": sched.semester,
            "year": sched.year,
            "message": f"{sched.semester} {sched.year} schedule has been finalized."
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


def delete_schedule(schedule_id: int) -> str:
    """Delete a Draft schedule and all its sections. Cannot delete Finalized schedules."""
    from .models import Schedule
    db = SessionLocal()
    try:
        sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not sched:
            return json.dumps({"error": f"Schedule {schedule_id} not found."})
        if sched.status == "Finalized":
            return json.dumps({"error": "Cannot delete a Finalized schedule. Contact the system administrator."})
        semester, year = sched.semester, sched.year
        section_count = db.query(Section).filter(Section.schedule_id == schedule_id).count()
        db.query(Section).filter(Section.schedule_id == schedule_id).delete()
        db.delete(sched)
        db.commit()
        return json.dumps({
            "status": "success",
            "message": f"Deleted {semester} {year} draft schedule and {section_count} section(s)."
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


def get_schedule_stats(schedule_id: int) -> str:
    """
    Return a load distribution summary for a generated schedule:
    sections per professor, core requirement coverage, and any unassigned sections.
    """
    from .models import Schedule
    db = SessionLocal()
    try:
        sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not sched:
            return json.dumps({"error": f"Schedule {schedule_id} not found."})

        sections = db.query(Section).filter(Section.schedule_id == schedule_id).all()

        # Load per professor
        load: dict = {}
        unassigned = 0
        for sec in sections:
            if sec.professor_id is None:
                unassigned += 1
                continue
            prof = db.query(Professor).filter(Professor.id == sec.professor_id).first()
            name = prof.name if prof else f"Prof #{sec.professor_id}"
            load[name] = load.get(name, 0) + 1

        # Core coverage
        core_flags = {"SSC": False, "HT": False, "GA": False, "WEM": False}
        for sec in sections:
            c = db.query(Course).filter(Course.id == sec.course_id).first()
            if c:
                if c.core_ssc: core_flags["SSC"] = True
                if c.core_ht:  core_flags["HT"]  = True
                if c.core_ga:  core_flags["GA"]  = True
                if c.core_wem: core_flags["WEM"] = True

        return json.dumps({
            "schedule_id": schedule_id,
            "semester": sched.semester,
            "year": sched.year,
            "status": sched.status,
            "total_sections": len(sections),
            "unassigned_sections": unassigned,
            "load_per_professor": load,
            "core_coverage": core_flags,
            "solver_log": sched.solver_log,
        })
    finally:
        db.close()


# =========================================================================
# Extended preference tools
# =========================================================================

def list_all_preferences(semester: str, year: int) -> str:
    """
    Summarize all preference records for a semester: who replied, who is
    approved, who is pending, and who is missing entirely.
    """
    db = SessionLocal()
    try:
        profs = db.query(Professor).filter(Professor.active == True).all()
        prefs = db.query(Preference).filter(
            Preference.semester == semester, Preference.year == year
        ).all()
        pref_by_prof = {p.professor_id: p for p in prefs}

        summary = []
        for prof in profs:
            pref = pref_by_prof.get(prof.id)
            if pref:
                summary.append({
                    "professor_id": prof.id,
                    "professor_name": prof.name,
                    "preference_id": pref.id,
                    "state": "approved" if pref.admin_approved else "pending",
                    "confidence": pref.confidence,
                    "has_parsed_json": pref.parsed_json is not None,
                })
            else:
                summary.append({
                    "professor_id": prof.id,
                    "professor_name": prof.name,
                    "preference_id": None,
                    "state": "missing",
                    "confidence": None,
                    "has_parsed_json": False,
                })

        counts = {
            "approved": sum(1 for s in summary if s["state"] == "approved"),
            "pending": sum(1 for s in summary if s["state"] == "pending"),
            "missing": sum(1 for s in summary if s["state"] == "missing"),
        }
        return json.dumps({"semester": semester, "year": year, "counts": counts, "professors": summary})
    finally:
        db.close()


def unapprove_preference(pref_id: int) -> str:
    """Revoke approval on a preference, setting admin_approved back to False."""
    db = SessionLocal()
    try:
        pref = db.query(Preference).filter(Preference.id == pref_id).first()
        if not pref:
            return json.dumps({"error": f"Preference {pref_id} not found."})
        if not pref.admin_approved:
            return json.dumps({"message": f"Preference {pref_id} is already unapproved."})
        pref.admin_approved = False
        db.commit()
        prof = db.query(Professor).filter(Professor.id == pref.professor_id).first()
        return json.dumps({
            "status": "success",
            "preference_id": pref_id,
            "professor_name": prof.name if prof else f"Prof #{pref.professor_id}",
            "message": "Approval revoked — preference is now pending review."
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


def delete_preference(pref_id: int) -> str:
    """Delete a preference record entirely (e.g. to allow re-submission)."""
    db = SessionLocal()
    try:
        pref = db.query(Preference).filter(Preference.id == pref_id).first()
        if not pref:
            return json.dumps({"error": f"Preference {pref_id} not found."})
        prof = db.query(Professor).filter(Professor.id == pref.professor_id).first()
        prof_name = prof.name if prof else f"Prof #{pref.professor_id}"
        db.delete(pref)
        db.commit()
        return json.dumps({
            "status": "success",
            "message": f"Preference for {prof_name} ({pref.semester} {pref.year}) has been deleted."
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


# =========================================================================
# Timeslot tools
# =========================================================================

def list_timeslots() -> str:
    """List all time slots in the system (active and inactive)."""
    db = SessionLocal()
    try:
        slots = db.query(TimeSlot).order_by(TimeSlot.days, TimeSlot.start_time).all()
        return json.dumps([{
            "id": s.id, "label": s.label, "days": s.days,
            "start_time": s.start_time, "end_time": s.end_time,
            "section_number": s.section_number, "max_classes": s.max_classes,
            "active": s.active
        } for s in slots])
    finally:
        db.close()


def toggle_timeslot(timeslot_id: int, active: bool) -> str:
    """Enable or disable a timeslot. Disabled timeslots are excluded from the solver."""
    db = SessionLocal()
    try:
        slot = db.query(TimeSlot).filter(TimeSlot.id == timeslot_id).first()
        if not slot:
            return json.dumps({"error": f"Timeslot {timeslot_id} not found."})
        slot.active = active
        db.commit()
        return json.dumps({
            "status": "success",
            "timeslot_id": timeslot_id,
            "label": slot.label,
            "active": slot.active,
            "message": f"Timeslot '{slot.label}' is now {'enabled' if active else 'disabled'}."
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


# =========================================================================
# Email history and reminders
# =========================================================================

def get_email_log(prof_id: int) -> str:
    """
    Retrieve the email communication history for a professor:
    all sent preference requests and received replies, newest first.
    """
    from .models import EmailLog
    db = SessionLocal()
    try:
        prof = db.query(Professor).filter(Professor.id == prof_id).first()
        if not prof:
            return json.dumps({"error": f"Professor {prof_id} not found."})
        logs = db.query(EmailLog).filter(EmailLog.professor_id == prof_id).order_by(EmailLog.sent_at.desc()).all()
        return json.dumps({
            "professor_name": prof.name,
            "email": prof.email,
            "log_count": len(logs),
            "logs": [{
                "id": l.id, "direction": l.direction, "subject": l.subject,
                "status": l.status, "sent_at": l.sent_at.isoformat()
            } for l in logs]
        })
    finally:
        db.close()


def send_reminder_email(prof_id: int, semester: str, year: int) -> str:
    """
    Send a follow-up reminder email to a professor who has not yet replied
    with their teaching preferences. Skips if they already have a preference record.
    """
    db = SessionLocal()
    try:
        existing = db.query(Preference).filter(
            Preference.professor_id == prof_id,
            Preference.semester == semester,
            Preference.year == year
        ).first()
        if existing:
            prof = db.query(Professor).filter(Professor.id == prof_id).first()
            return json.dumps({
                "message": f"{prof.name if prof else f'Prof #{prof_id}'} already has a preference record for {semester} {year}. No reminder sent."
            })
    finally:
        db.close()
    # Reuse the same send function — it drafts a new email with previous schedule context
    result = send_preference_email(prof_id, semester, year)
    return json.dumps({"status": "reminder_sent", "result": result})


# =========================================================================
# Constraint tools
# =========================================================================

def list_constraints() -> str:
    """List all scheduling constraints (hard and soft rules used by the solver)."""
    from .models import Constraint
    db = SessionLocal()
    try:
        constraints = db.query(Constraint).all()
        if not constraints:
            return json.dumps({"message": "No constraints found."})
        return json.dumps([{
            "id": c.id, "type": c.type, "name": c.name,
            "description": c.description, "value_json": c.value_json,
            "active": c.active,
        } for c in constraints])
    finally:
        db.close()


def update_constraint(
    constraint_id: int,
    active: Optional[bool] = None,
    value_json: Optional[dict] = None,
    description: Optional[str] = None,
) -> str:
    """
    Update an existing constraint. Use this to toggle constraints on/off,
    change their parameters (value_json), or update descriptions.
    """
    from .models import Constraint
    db = SessionLocal()
    try:
        c = db.query(Constraint).filter(Constraint.id == constraint_id).first()
        if not c:
            return json.dumps({"error": f"Constraint {constraint_id} not found."})
        if active is not None:
            c.active = active
        if value_json is not None:
            c.value_json = value_json
        if description is not None:
            c.description = description
        db.commit()
        return json.dumps({
            "status": "success",
            "id": c.id, "name": c.name, "active": c.active,
            "value_json": c.value_json,
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


def get_prime_time_config() -> str:
    """
    Get the current prime-time constraint configuration.
    Returns start_time, end_time, max_percentage, and whether it is active.
    """
    from .models import Constraint
    db = SessionLocal()
    try:
        c = db.query(Constraint).filter(Constraint.name == "prime_time").first()
        if not c:
            return json.dumps({"message": "No prime-time constraint configured."})
        return json.dumps({
            "id": c.id, "active": c.active,
            "start_time": c.value_json.get("start_time"),
            "end_time": c.value_json.get("end_time"),
            "max_percentage": c.value_json.get("max_percentage"),
            "description": c.description,
        })
    finally:
        db.close()


def update_prime_time_config(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_percentage: Optional[int] = None,
    active: Optional[bool] = None,
) -> str:
    """
    Update the prime-time constraint parameters. Only provided fields are changed.
    - start_time / end_time: HH:MM format (e.g. "09:00", "14:00")
    - max_percentage: 0-100, the max % of total sections allowed in the window
    - active: True/False to enable/disable the constraint entirely
    """
    from .models import Constraint
    db = SessionLocal()
    try:
        c = db.query(Constraint).filter(Constraint.name == "prime_time").first()
        if not c:
            # Auto-create if not seeded yet
            c = Constraint(
                type="hard",
                name="prime_time",
                value_json={"start_time": "09:00", "end_time": "14:00", "max_percentage": 60},
                description="Prime-time cap",
                active=True,
            )
            db.add(c)

        cfg = dict(c.value_json or {})
        if start_time is not None:
            cfg["start_time"] = start_time
        if end_time is not None:
            cfg["end_time"] = end_time
        if max_percentage is not None:
            cfg["max_percentage"] = max_percentage
        c.value_json = cfg
        if active is not None:
            c.active = active
        db.commit()
        return json.dumps({
            "status": "success",
            "active": c.active,
            "start_time": cfg["start_time"],
            "end_time": cfg["end_time"],
            "max_percentage": cfg["max_percentage"],
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"error": str(e)})
    finally:
        db.close()


# =========================================================================
# Tool registry — used by chat.py to register tools with Gemini
# =========================================================================

ALL_TOOLS = [
    # Read / lookup
    get_professor,
    list_professors,
    get_courses,
    get_unreplied_professors,
    list_timeslots,
    list_constraints,
    # Email
    trigger_send_preference_email,
    trigger_send_all_preference_emails,
    send_reminder_email,
    get_email_log,
    trigger_poll_unread_replies,
    # Preferences
    get_preference,
    get_professor_preference,
    list_all_preferences,
    extract_and_save_preference_json,
    create_manual_preference,
    approve_preference,
    unapprove_preference,
    delete_preference,
    # Solver & schedules
    run_preflight_checks,
    trigger_solver,
    list_schedules,
    finalize_schedule,
    delete_schedule,
    get_schedule_stats,
    # Professor CRUD
    create_professor,
    update_professor,
    deactivate_professor,
    # Course CRUD
    create_course,
    update_course,
    delete_course,
    # Timeslots
    toggle_timeslot,
    # Constraints
    update_constraint,
    get_prime_time_config,
    update_prime_time_config,
]

TOOL_REGISTRY = {func.__name__: func for func in ALL_TOOLS}

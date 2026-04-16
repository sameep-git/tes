"""
One-time migration script: re-parse all existing preference emails using the
new AI prompt so that course_assignments (with quantities & timeslot pairings)
are correctly extracted.

If an email can't be re-parsed (no raw_email stored, or AI fails), we fall
back to a mechanical conversion: each entry in preferred_courses becomes a
single course_assignment with timeslot=null.

Usage (from inside the backend container or local venv):
    python reparse_all_preferences.py
"""
import os, sys

from backend.database import SessionLocal
from backend.models import Preference
from backend.ai import extract_preferences_from_email
from sqlalchemy.orm.attributes import flag_modified


def _fallback_migration(pref_row, data: dict):
    """Convert old preferred_courses list → course_assignments with null timeslots."""
    print("  Fallback: converting preferred_courses → course_assignments (no timeslot info)")
    course_assignments = []
    for course in data.get("preferred_courses", []):
        course_assignments.append({"course": course, "timeslot": None})

    data["course_assignments"] = course_assignments
    # Keep the old fields around so nothing breaks downstream
    pref_row.parsed_json = dict(data)
    flag_modified(pref_row, "parsed_json")


def run_migration(reparse: bool = True):
    db = SessionLocal()
    try:
        prefs = db.query(Preference).all()
        reparsed = 0
        fallback = 0
        skipped = 0

        for p in prefs:
            if not p.parsed_json:
                continue

            data = p.parsed_json

            # Already migrated?
            if data.get("course_assignments"):
                print(f"  [SKIP] Preference {p.id} (prof {p.professor_id}) — already has course_assignments")
                skipped += 1
                continue

            print(f"  [MIGRATE] Preference {p.id} (prof {p.professor_id}, {p.semester} {p.year})")

            if reparse and p.raw_email:
                try:
                    new_parsed = extract_preferences_from_email(p.raw_email)
                    new_data = new_parsed.dict()
                    # Preserve admin approval status
                    p.parsed_json = new_data
                    p.confidence = new_data.get("confidence_score")
                    flag_modified(p, "parsed_json")
                    reparsed += 1
                    print(f"    → AI re-parsed: {len(new_data.get('course_assignments', []))} assignments")
                except Exception as e:
                    print(f"    → AI failed ({e}), using fallback")
                    _fallback_migration(p, data)
                    fallback += 1
            else:
                _fallback_migration(p, data)
                fallback += 1

        db.commit()
        print(f"\nDone! Re-parsed: {reparsed} | Fallback: {fallback} | Skipped: {skipped}")

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Preference Migration: preferred_courses → course_assignments")
    print("=" * 60)
    print()
    run_migration(reparse=True)

import os
import json
from typing import Optional, List
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

from .database import SessionLocal
from .models import Course, TimeSlot

load_dotenv()

client = genai.Client() if os.getenv("GEMINI_API_KEY") else None

class ParsedPreference(BaseModel):
    # Load
    requested_load: Optional[int] = None        # soft: "I'd like 2 sections"
    max_load: Optional[int] = None              # hard: "I cannot do more than 2"

    # Course preferences
    preferred_courses: List[str] = []           # specific codes: ["ECON 30223"]
    avoid_courses: List[str] = []
    preferred_levels: List[int] = []            # [30000, 40000] for upper-division only

    # Time preferences — normalized against DB timeslot labels
    preferred_timeslots: List[str] = []         # matched to TimeSlot.label values
    avoid_timeslots: List[str] = []
    avoid_days: List[str] = []                  # ["M", "T", "W", "R", "F"] — day-level avoidance

    # Scheduling style
    wants_back_to_back: Optional[bool] = None   # True=wants it, False=avoid it, None=no pref

    # Special status
    on_leave: bool = False                      # triggers professor.active = False immediately

    # Overflow
    notes_for_admin: Optional[str] = None       # anything Gemini can't map to a field
    confidence_score: float                     # 0.0-1.0, Gemini self-reports how sure it is

def extract_preferences_from_email(email_text: str) -> ParsedPreference:
    """
    Takes raw email text, pulls available courses and timeslots from the DB 
    to provide as context, and asks Gemini to extract a ParsedPreference object.
    """
    if not client:
        raise ValueError("GEMINI_API_KEY not found in environment.")

    db = SessionLocal()
    try:
        # 1. Get valid courses and timeslots so Gemini knows what to match against
        courses = db.query(Course).all()
        timeslots = [str(t.label) for t in db.query(TimeSlot).filter(TimeSlot.active == True).all()]
        # Build a rich course listing: code + name so the model can resolve either
        course_listing = "\n".join(
            f"  - {c.code} | {c.name} | Level {c.level}"
            for c in courses
        )
    finally:
        db.close()

    # 2. Construct the prompt
    prompt = f"""
    You are an expert administrative assistant for a university Economics Department.
    A professor has replied to an email asking for their teaching preferences for the upcoming semester.
    
    Your job is to read their email and extract their preferences into a strict JSON structure.
    
    ===== VALID COURSE CATALOG =====
    Format: CODE | Name | Level
{course_listing}
    
    ===== VALID TIMESLOT LABELS =====
    {', '.join(timeslots)}
    
    ===== VALID DAYS =====
    M (Monday), T (Tuesday), W (Wednesday), R (Thursday), F (Friday)
    
    ===== EXTRACTION RULES =====
    
    COURSES (most important — read carefully):
    1. Extract course preferences into the `preferred_courses` or `avoid_courses` fields using the exact CODE (e.g. "ECON 30223" or "ECON 40970").
    2. Professors may refer to courses by name ("Intermediate Micro"), partial name ("Micro"), level ("upper division", "300-level"), or code. Match intelligently against the catalog above.
    3. IMPORTANT: The catalog contains duplicate base codes for special topics (e.g. multiple ECON 40970s). You MUST carefully read the course name they provide and pick the exact code + name match from the catalog. If they omit the name for a special topic, add a note in `notes_for_admin` and pick the closest match or leave it out if completely ambiguous.
    4. If they say "my usual courses" or reference prior semesters without specifics, set `notes_for_admin` with the quote and lower confidence.
    5. If a name only partially matches, pick the closest code AND note ambiguity in `notes_for_admin`.
    6. NEVER invent a course code not in the catalog. If you cannot match, put the unmatched text in `notes_for_admin`.
    6. `preferred_levels` should contain numeric level values like 10000, 30000, 40000 (matching the Level field in the catalog).
    
    TIMESLOTS:
    7. Map all time requests strictly to Valid TimeSlot Labels. Do not invent labels.
    8. "Morning" → earlier timeslots in the list. "Afternoon" → later timeslots. Pick the closest matches.
    9. Section numbers in the email (e.g. "section 002", "section 050") correspond to timeslot labels — use them to narrow down the match where possible.
    
    LOAD:
    10. `requested_load` = how many sections they want (e.g. "I'd like to teach 2 courses" → 2).
    11. `max_load` = the maximum they can handle (e.g. "I can do at most 3" → 3).
    
    GENERAL:
    12. If a preference is ambiguous or can't be cleanly mapped, add it verbatim to `notes_for_admin` and lower `confidence_score`.
    13. `confidence_score` MUST be a float between 0.0 and 1.0. 1.0 = perfectly clear email with exact codes. 0.5 or below = email is vague or contradictory.
    14. If the professor says they are on leave or sabbatical, set `on_leave: true`.
    
    ===== PROFESSOR'S EMAIL =====
    \"\"\"
    {email_text}
    \"\"\"
    """

    # 3. Call Gemini with Structured Outputs
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': ParsedPreference,
            'temperature': 0.1,
        }
    )

    # 4. Parse the returned JSON back into our Pydantic Model
    try:
        resp_text = response.text or "{}"
        extracted_data = json.loads(resp_text)
        return ParsedPreference(**extracted_data)
    except Exception as e:
        print(f"Failed to parse Gemini output: {e}")
        print(f"Raw Output was: {response.text}")
        return ParsedPreference(
            confidence_score=0.0,
            notes_for_admin=f"FAILED TO PARSE AI RESPONSE: {str(e)}"
        )
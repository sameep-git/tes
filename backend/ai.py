import os
import json
from typing import Optional, List
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

from .database import SessionLocal
from .models import Course, TimeSlot

load_dotenv()

client = genai.Client(
    vertexai=True,
    project=os.getenv("VERTEX_PROJECT_ID"),
    location=os.getenv("VERTEX_LOCATION", "us-central1"),
)

class CourseAssignment(BaseModel):
    course: str               # Full course key from catalog: "ECON 10223 | Intro Microeconomics"
    timeslot: Optional[str] = None  # "MWF 9:00am" if prof specified a time, else null

class ParsedPreference(BaseModel):
    # Load
    requested_load: Optional[int] = None        # soft: "I'd like 2 sections"
    max_load: Optional[int] = None              # hard: "I cannot do more than 2"

    # Course assignments (replaces preferred_courses + preferred_timeslots)
    # Each entry = one desired section. Same course can appear multiple times.
    # e.g. [{course: "ECON 10223 | Intro Micro", timeslot: "MWF 9:00am"},
    #        {course: "ECON 10223 | Intro Micro", timeslot: null},
    #        {course: "ECON 40990 | Internship",  timeslot: null}]
    course_assignments: List[CourseAssignment] = []

    avoid_courses: List[str] = []
    preferred_levels: List[int] = []            # [30000, 40000] for upper-division only

    # Time preferences — normalized against DB timeslot labels
    avoid_timeslots: List[str] = []
    avoid_days: List[str] = []                  # ["M", "T", "W", "R", "F"] — day-level avoidance

    # Scheduling style
    wants_back_to_back: Optional[bool] = None   # True=wants it, False=avoid it, None=no pref

    # Special status
    on_leave: bool = False                      # triggers professor.active = False immediately

    # Overflow
    notes_for_admin: Optional[str] = None       # anything the AI can't map to a field
    confidence_score: float                     # 0.0-1.0, AI self-reports how sure it is

def extract_preferences_from_email(email_text: str) -> ParsedPreference:
    """
    Takes raw email text, pulls available courses and timeslots from the DB 
    to provide as context, and asks Gemini to extract a ParsedPreference object.
    """
    if not client:
        raise ValueError("Vertex AI credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS, VERTEX_PROJECT_ID and VERTEX_LOCATION.")

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
    
    COURSE ASSIGNMENTS (most important — read carefully):
    1. Build `course_assignments` as a list of objects, one per DESIRED SECTION.
       Each object has: {{"course": "<FULL COURSE KEY>", "timeslot": "<LABEL or null>"}}
    2. If a professor wants MULTIPLE SECTIONS of the same course, add a SEPARATE ENTRY for each section.
       Example: "I'd like to teach 2 sections of Intro Micro" →
         [{{"course": "ECON 10223 | Intro Microeconomics", "timeslot": null}},
          {{"course": "ECON 10223 | Intro Microeconomics", "timeslot": null}}]
    3. Use the EXACT COURSE KEY from the catalog ("CODE | Name"). Never invent codes.
    4. If they specify a time for a course ("Intro Micro in the morning"), match to a Valid Timeslot Label.
       If no time mentioned, set timeslot to null.
    5. The catalog contains duplicate base codes for special topics (e.g. multiple ECON 40970s).
       Pick the exact code+name match. If ambiguous, add a note in `notes_for_admin`.
    6. If they say "my usual courses" without specifics, set `notes_for_admin` and lower confidence.
    7. NEVER put a course in both `course_assignments` and `avoid_courses`.

    AVOID COURSES:
    8. List courses the professor explicitly does NOT want in `avoid_courses` using full course keys.

    LEVELS:
    9. `preferred_levels` should contain numeric level values like 10000, 30000, 40000.
       Only add these if the professor expresses a level preference BEYOND their specific course requests.

    TIMESLOT AVOIDANCE:
    10. Map time avoidance to Valid TimeSlot Labels in `avoid_timeslots`.
    11. Day-level avoidance (e.g. "no Fridays") goes in `avoid_days` as single letters.

    LOAD:
    12. `requested_load` = how many sections they want total.
    13. `max_load` = the maximum they can handle.
    
    GENERAL:
    14. If a preference is ambiguous, add it verbatim to `notes_for_admin` and lower `confidence_score`.
    15. `confidence_score` MUST be 0.0-1.0. 1.0 = perfectly clear. 0.5 or below = vague/contradictory.
    16. If the professor says they are on leave or sabbatical, set `on_leave: true`.
    
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
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
    preferred_courses: List[str] = []           # specific codes: ["ECON 301"]
    avoid_courses: List[str] = []
    preferred_levels: List[int] = []            # [300, 400] for upper-division only

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
        courses = [str(c.code) for c in db.query(Course).all()]
        timeslots = [str(t.label) for t in db.query(TimeSlot).filter(TimeSlot.active == True).all()]
    finally:
        db.close()

    # 2. Construct the prompt
    prompt = f"""
    You are an expert administrative assistant for an Economics Department.
    A professor has replied to an email asking for their teaching preferences for the upcoming semester.
    
    Your job is to read their email and extract their preferences into a strict JSON structure.
    
    IMPORTANT CONTEXT:
    - Valid Course Codes in our system: {', '.join(courses)}
    - Valid TimeSlot Labels in our system: {', '.join(timeslots)}
    - Valid Days: M, T, W, R (Thursday), F
    
    RULES:
    1. Map their course requests strictly to the Valid Course Codes provided above. Do not invent course codes.
    2. Map their time requests strictly to the Valid TimeSlot Labels provided above.
    3. If they ask for "Mornings", map that to the 9:00am, 9:30am, 10:00am, or 11:00am timeslots.
    4. If they ask for "Afternoons", map that to the 1:00pm, 2:30pm timeslots.
    5. If a preference is ambiguous or contradicts the system, add it to `notes_for_admin` and lower the `confidence_score`.
    6. `confidence_score` MUST be a float between 0.0 and 1.0. If you are very certain, use 0.9 or 1.0. If the email is confusing, use 0.5 or lower.
    
    PROFESSOR'S EMAIL:
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
            # We enforce a slightly lower temperature so it doesn't get overly creative
            'temperature': 0.1, 
        }
    )

    # 4. Parse the returned JSON back into our Pydantic Model
    try:
        # Gemini returns a stringified JSON that perfectly matches our schema
        resp_text = response.text or "{}"
        extracted_data = json.loads(resp_text)
        return ParsedPreference(**extracted_data)
    except Exception as e:
        print(f"Failed to parse Gemini output: {e}")
        print(f"Raw Output was: {response.text}")
        # Return a fallback with a 0.0 confidence score if it completely breaks
        return ParsedPreference(
            confidence_score=0.0,
            notes_for_admin=f"FAILED TO PARSE AI RESPONSE: {str(e)}"
        )
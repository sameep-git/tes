import json
import os
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types

from ..database import SessionLocal
from ..models import Professor, Schedule, Constraint, Preference, Course
from ..email import send_preference_email, poll_unread_replies
from ..ai import extract_preferences_from_email
from ..solver import run_solver

router = APIRouter(prefix="/api/chat", tags=["chat"])

client = genai.Client() if os.getenv("GEMINI_API_KEY") else None

# -------------------------------------------------------------------------
# Python Tool Wrappers (Exposing exactly what FastMCP exposed)
# -------------------------------------------------------------------------

def get_professor(prof_id: int) -> str:
    """Retrieve professor details by their ID."""
    db = SessionLocal()
    try:
        prof = db.query(Professor).filter(Professor.id == prof_id).first()
        if not prof:
            return json.dumps({"error": f"Professor with ID {prof_id} not found."})
        
        prof_data = {
            "id": prof.id, "name": prof.name, "email": prof.email,
            "office": prof.office, "rank": prof.rank,
            "max_sections": prof.max_sections, "active": prof.active
        }
        return json.dumps(prof_data)
    finally:
        db.close()

def get_courses() -> str:
    """Retrieve all available courses and their core requirements."""
    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        courses_data = []
        for c in courses:
            courses_data.append({
                "id": c.id, "code": c.code, "name": c.name, "credits": c.credits,
                "level": c.level, "min_sections": c.min_sections, "max_sections": c.max_sections,
                "requires_lab": c.requires_lab, "core_ssc": c.core_ssc,
                "core_ht": c.core_ht, "core_ga": c.core_ga, "core_wem": c.core_wem
            })
        return json.dumps(courses_data)
    finally:
        db.close()

def get_unreplied_professors(year: int, semester: str) -> str:
    """Retrieve professors who have not replied yet for the given year and semester."""
    db = SessionLocal()
    try:
        subquery = db.query(Preference.professor_id).filter(
            Preference.year == year, Preference.semester == semester
        ).scalar_subquery()
        
        unreplied_professors = db.query(Professor).filter(
            Professor.active == True, Professor.id.notin_(subquery)
        ).all()

        if not unreplied_professors:
            return json.dumps({"message": "All active professors have replied for this semester."})
        
        unreplied_professors_data = []
        for prof in unreplied_professors:
            unreplied_professors_data.append({
                "id": prof.id, "name": prof.name, "email": prof.email, "active": prof.active
            })
        return json.dumps(unreplied_professors_data)
    finally:
        db.close()

def trigger_poll_unread_replies() -> str:
    """Poll the system email inbox for any unread preference replies and save them to the database."""
    replies = poll_unread_replies()
    return json.dumps({"processed_count": len(replies), "replies": replies})

def trigger_solver(semester: str, year: int) -> str:
    """Run the Constraint Solver to generate a schedule for the given semester and year."""
    result = run_solver(semester, year)
    return json.dumps(result)

# Registry of available tools for Gemini to call
tool_registry = {
    "get_professor": get_professor,
    "get_courses": get_courses,
    "get_unreplied_professors": get_unreplied_professors,
    "trigger_poll_unread_replies": trigger_poll_unread_replies,
    "trigger_solver": trigger_solver
}

# -------------------------------------------------------------------------
# Streaming API Endpoint
# -------------------------------------------------------------------------

@router.post("/")
async def chat_endpoint(request: Request):
    """
    Handles streaming chat interactions with Gemini using Server-Sent Events (SSE).
    Allows the frontend to see real-time tool execution logs before seeing the final text.
    """
    if not client:
        return StreamingResponse(
            iter(["data: " + json.dumps({"type": "error", "content": "GEMINI_API_KEY missing"}) + "\n\n"]),
            media_type="text/event-stream"
        )

    data = await request.json()
    user_message = data.get("message", "")
    
    # We maintain a minimal conversation history array here.
    # In a fully production app, we would store this history in a database or frontend context.
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_message)])]

    async def event_stream() -> AsyncGenerator[str, None]:
        # Provide Gemini with our tools
        config = types.GenerateContentConfig(
            tools=[
                get_professor, 
                get_courses, 
                get_unreplied_professors, 
                trigger_poll_unread_replies, 
                trigger_solver
            ],
            temperature=0.4,
            system_instruction=(
                "You are the AI assistant for the TCU Econ Scheduler (TES) system. "
                "You help the department chair manage professor preferences and generate schedules. "
                "Always check if all professors have replied using get_unreplied_professors before allowing "
                "the solver to run. Be concise and professional."
            )
        )

        try:
            # First, send the message to Gemini and check if it wants to use a tool
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=config
            )

            # If Gemini decided to call a function:
            if response.function_calls:
                for function_call in response.function_calls:
                    tool_name = function_call.name
                    tool_args = function_call.args
                    
                    # 1. Yield an SSE event telling the UI we are executing a tool
                    yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_name})}\n\n"
                    await asyncio.sleep(0.1)  # tiny pause for UI to catch up

                    # 2. Execute the python function locally
                    tool_func = tool_registry.get(tool_name)
                    tool_result = ""
                    if tool_func:
                        try:
                            # Safely pass the arguments unpacked
                            tool_result = tool_func(**tool_args)
                        except Exception as e:
                            tool_result = json.dumps({"error": str(e)})
                    else:
                        tool_result = json.dumps({"error": f"Tool {tool_name} not found locally."})

                    # 3. Feed the result back into the content history for Gemini
                    contents.append(response.candidates[0].content) # Append Assistant's function call request
                    contents.append(
                        types.Content(
                            role="tool", 
                            parts=[types.Part.from_function_response(name=tool_name, response={"result": tool_result})]
                        )
                    )

                # 4. Ask Gemini to generate the final response now that it has the tool data
                # We use generate_content_stream to get that cool word-by-word typewriter effect
                response_stream = client.models.generate_content_stream(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=config
                )
                for chunk in response_stream:
                    if chunk.text:
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk.text})}\n\n"
                        await asyncio.sleep(0.01)

            # If Gemini just wanted to talk normally (no tools needed):
            else:
                if response.text:
                    # In a real app we'd stream this too, but for simplicity if it didn't call a tool, we yield the block
                    yield f"data: {json.dumps({'type': 'text', 'content': response.text})}\n\n"

            # 5. Tell the UI we are done
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
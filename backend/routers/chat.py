import json
import os
import asyncio
import sys
import traceback
from typing import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types

from ..tools import ALL_TOOLS, TOOL_REGISTRY

router = APIRouter(prefix="/api/chat", tags=["chat"])

client = genai.Client() if os.getenv("GEMINI_API_KEY") else None

# -------------------------------------------------------------------------
# System Instruction with Guardrails
# -------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """\
You are the AI assistant for the TCU Econ Scheduler (TES) system.
You help the department chair manage professors, courses, preferences, and generate schedules.

## YOUR TOOLS
You have access to tools for:
- Viewing professors, courses, history, and preferences
- Creating, updating, and deleting professors and courses
- Polling email for preference replies and auto-parsing them
- Creating manual preferences for missing professors
- Approving preferences
- Running pre-flight checks and the constraint solver

## STRICT RULES — YOU MUST FOLLOW THESE

### NEVER Ask the User for IDs
1. NEVER ask "what is the professor ID?" or "what is the preference ID?" — this is unacceptable.
2. If you need a professor's ID, call `list_professors()` first and find them by name.
3. If you need a preference ID, call `get_professor_preference(prof_id, semester, year)` after looking up the professor.
4. If you need a course ID, call `get_courses()` and match by code or name.
5. If the user asks about past history or who taught a class, call `get_course_history(course_id)` after resolving the course_id.
6. Always resolve names → IDs yourself using your tools before taking action.

### Always Chain Tools Automatically
7. After polling (`trigger_poll_unread_replies`), the extraction and auto-approval run automatically. Report:
   - How many were auto-approved
   - Which prefs need manual review and why (low confidence, on_leave, admin notes)
8. After `approve_preference`, the tool returns preflight status. Report it immediately:
   - If `ready: true` → tell the user they can now run the solver
   - If blockers remain → list them and offer to fix each one
9. Never make the user ask for the next obvious step — anticipate it and do it.

### Solver Guardrail
10. Before EVER calling `trigger_solver`, you MUST call `run_preflight_checks` first.
11. If `run_preflight_checks` returns `ready: false`, REFUSE to run the solver.
    Explain each blocker and offer to fix them (create preference, approve, etc.).

### Data Integrity
12. Use `deactivate_professor` (soft delete) — professors may appear in historical schedules.
13. `delete_course` will refuse if sections reference it — explain this clearly to the user.

### Communication Style
- Be concise and professional.
- Use markdown tables for structured data.
- Summarize tool results in plain language — never dump raw JSON at the user.
- Confirm destructive actions (deletes, deactivation) before proceeding.
"""

# -------------------------------------------------------------------------
# Streaming API Endpoint
# -------------------------------------------------------------------------

@router.post("")
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
    history = data.get("history", [])  # List of {role, content} from the frontend

    # Build the full conversation content from history + new message
    # History roles from frontend: 'user' | 'assistant' → Gemini roles: 'user' | 'model'
    contents = []
    for msg in history:
        role = "model" if msg.get("role") == "assistant" else "user"
        content = msg.get("content", "").strip()
        if content:  # Skip empty placeholders
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))

    # Append the new user message
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    async def event_stream() -> AsyncGenerator[str, None]:
        config = types.GenerateContentConfig(
            tools=ALL_TOOLS,
            temperature=0.4,
            system_instruction=SYSTEM_INSTRUCTION
        )

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=config
            )

            # Handle function calls (may be multiple rounds)
            max_rounds = 5  # Safety limit to prevent infinite tool loops
            round_count = 0

            while response.function_calls and round_count < max_rounds:
                round_count += 1

                # Append the model's response ONCE per round (not once per function call)
                # to avoid duplicating the same model message in context when Gemini
                # returns multiple parallel tool calls in a single response.
                contents.append(response.candidates[0].content)

                for function_call in response.function_calls:
                    tool_name = function_call.name
                    tool_args = function_call.args

                    # 1. Yield SSE event telling the UI we are executing a tool
                    yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_name})}\n\n"
                    await asyncio.sleep(0.1)

                    # 2. Execute the python function locally
                    tool_func = TOOL_REGISTRY.get(tool_name)
                    if tool_func:
                        try:
                            tool_result = tool_func(**tool_args)
                        except Exception as e:
                            tool_result = json.dumps({"error": str(e)})
                    else:
                        tool_result = json.dumps({"error": f"Tool {tool_name} not found."})

                    # 3. Each tool response is its own Content block — Gemini requires
                    # one Content per function response, not batched into one block.
                    contents.append(
                        types.Content(
                            role="tool",
                            parts=[types.Part.from_function_response(
                                name=tool_name,
                                response={"result": tool_result}
                            )]
                        )
                    )

                # 4. Ask Gemini for the next response (may call more tools or produce text)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=config
                )

            # Safety limit reached — Gemini is still requesting tools but we
            # must stop to avoid infinite loops. Surface this to the user.
            if response.function_calls:
                yield f"data: {json.dumps({'type': 'error', 'content': 'The agent reached its maximum tool-call limit (5 rounds) without producing a final answer. Please rephrase or break your request into smaller steps.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Stream the final text response.
            # IMPORTANT: Yield response.text directly rather than re-calling
            # generate_content_stream, which would let Gemini invoke tools again
            # (causing double sends, etc.)
            if response.text:
                words = response.text.split(' ')
                for i, word in enumerate(words):
                    chunk = word if i == len(words) - 1 else word + ' '
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.01)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_trace = traceback.format_exc()
            print("FATAL CHAT ERROR:", error_trace, file=sys.stderr)
            sys.stderr.flush()
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
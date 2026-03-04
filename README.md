# TES — TCU Econ Scheduler

An AI-powered scheduling system for the TCU Economics department. The AI agent manages the full workflow: sending preference emails to professors, parsing replies, running a constraint solver, and generating semester teaching schedules.

---

## Architecture

```
frontend/   Next.js 16 dashboard + AI chat panel (TanStack Query for data fetching)
backend/    FastAPI + SQLAlchemy + OR-Tools solver
            └─ Gmail API for email send/receive
            └─ Gemini AI for preference extraction + agent chat
scheduler.db  SQLite database (auto-created on first run)
```

---

## Quick Start (Docker — recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/app/apikey)
- `credentials.json` — Gmail OAuth client credentials from Google Cloud Console
- `token.json` — auto-generated on first interactive login (see Gmail setup below)

### 1. Configure environment
```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### 2. Run
```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

The database is stored in a Docker volume (`db_data`) and persists across restarts.

---

## Quick Start (Local Dev)

### Backend
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # set GEMINI_API_KEY
uvicorn backend.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                       # runs on http://localhost:3000
```

---

## Gmail Setup (Required for email features)

The system uses the Gmail API to send preference request emails and poll for replies.

### One-time setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Enable **Gmail API**
2. Create an OAuth 2.0 client ID → Download as `credentials.json` → place at project root
3. Run the interactive auth flow once to generate `token.json`:
   ```bash
   source venv/bin/activate
   python -c "from backend.email import get_gmail_service; get_gmail_service(server_mode=False)"
   ```
   A browser window will open — log in with the department Gmail account.
4. `token.json` is now saved at the project root. The backend uses it for all future API calls.

> **Docker:** Mount both files as shown in `docker-compose.yml`. The token auto-refreshes (mounted writable); no need to re-run the flow unless access is revoked.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | From [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `DATABASE_URL` | No | SQLite path — default `sqlite:///./scheduler.db`, Docker uses `/data/scheduler.db` |

---

## AI Agent Capabilities (32 tools)

The chat panel talks to a Gemini agent with full tool access:

| Category | Tools |
|---|---|
| **Professors** | list, get, create, update, deactivate |
| **Courses** | list, create, update, delete |
| **Timeslots** | list, enable/disable |
| **Email** | send to one prof, send to all unreplied, send reminder, get email log |
| **Preferences** | poll inbox, view, list all, extract JSON, create manually, approve, unapprove, delete |
| **Solver** | preflight checks, run solver, finalize schedule, delete draft, get stats |
| **Constraints** | list active constraints |
| **Guardrails** | run preflight checks, create manual preference, approve preference |

### Automatic pipelines
- **Poll → Extract → Auto-approve**: When the inbox is polled, replies are immediately AI-parsed. High-confidence preferences (≥ 85%, no leave, no admin notes) are auto-approved.
- **Approve → Preflight**: After any approval, the agent immediately reports whether the system is ready to run the solver.
- The agent never asks you for IDs — it looks them up by name using its tools.
- Up to 5 rounds of tool-calling per message (multi-hop reasoning).

---

## Project Structure

```
backend/
  main.py          FastAPI app, CORS, background scheduler
  models.py        SQLAlchemy ORM models
  schemas.py       Pydantic request/response schemas
  database.py      DB session setup
  tools.py         All 32 AI-callable tool functions
  email.py         Gmail API send/poll logic
  ai.py            Preference extraction via Gemini
  solver.py        OR-Tools constraint solver
  routers/
    chat.py        Streaming AI chat endpoint (SSE, multi-round tool loop)
    professors.py  Professor CRUD API
    courses.py     Course listing API
    preferences.py Preference listing + approval API
    schedules.py   Schedule listing API
    health.py      Health check

frontend/
  src/
    app/
      layout.tsx     Root layout — wraps app in QueryClientProvider
    lib/
      api.ts         Shared API fetch functions, query keys, and TypeScript interfaces
    components/
      providers.tsx  TanStack Query provider (30s stale time, background refetch)
      dashboard.tsx  Main dashboard — independent per-tab data loading via useQuery
      chat-panel.tsx Streaming AI chat with markdown + drag-to-scroll table rendering
```

---

## Background Email Polling

The backend automatically polls the Gmail inbox every **15 minutes** for new preference replies. Each poll runs the full pipeline: detect → extract → auto-approve (if confidence ≥ 85%).

To disable, remove the `scheduler.add_job(...)` call in `backend/main.py`.

---

Copyright (c) 2026 Sameep Shah. All rights reserved.

No part of this source code may be used, copied, modified, merged, published,
distributed, sublicensed, or sold without the express prior written permission
of the copyright holder.

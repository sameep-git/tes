# TES — TCU Econ Scheduler

A distributed scheduling system designed for the TCU Economics department. The software automates the semester scheduling workflow: polling professor preferences via the Gmail API, parsing responses into structured data via Vertex AI, and generating optimized teaching schedules using an integer programming solver running on AWS Lambda.

---

## Architecture

```text
frontend/       Next.js 16 dashboard (TanStack Query for state management)
backend/        FastAPI + SQLAlchemy + Alembic (Database Migrations)
                └─ Gmail API (Email polling & dispatch)
                └─ Google Cloud Vertex AI (Preference parsing & natural language interface)
lambda_solver/  AWS Lambda container running Google OR-Tools constraint solver
scheduler.db    SQLite database (managed via Alembic)
```

---

## Quick Start (Docker — recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Google Cloud Service Account credentials (`vertex_key.json`) with Vertex AI permissions
- `credentials.json` — Gmail OAuth client credentials from Google Cloud Console
- `token.json` — Auto-generated on first interactive login (see Gmail setup below)
- AWS IAM credentials with permissions to invoke the Lambda solver

### 1. Configure environment
```bash
cp .env.example .env
# Edit .env to include your AWS and Google Cloud configurations
```

### 2. Run
```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

The database is stored in an isolated Docker volume (`db_data`) and persists across container restarts. Alembic migrations run automatically on container startup.

---

## Quick Start (Local Development)

### Backend
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

cp .env.example .env              # Set required environment variables
uvicorn backend.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                       # runs on http://localhost:3000
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `VERTEX_PROJECT_ID` | ✅ | Google Cloud project ID for Vertex AI |
| `VERTEX_LOCATION` | ✅ | Google Cloud region (e.g., `us-central1`) |
| `AWS_ACCESS_KEY_ID` | ✅ | AWS IAM Access Key |
| `AWS_SECRET_ACCESS_KEY`| ✅ | AWS IAM Secret Key |
| `AWS_REGION` | ✅ | AWS Region (e.g., `us-east-1`) |
| `SOLVER_LAMBDA_FUNCTION`| ✅ | Name of the AWS Lambda solver function |
| `DATABASE_URL` | No | SQLite connection string — default `sqlite:///./scheduler.db` |
| `CORS_ORIGINS` | No | Allowed frontend origins |
| `TES_ADMIN_TOKEN` | No | API authentication token |

*(Note: Do not commit `.env`, `vertex_key.json`, `credentials.json`, or `token.json` to version control.)*

---

## Gmail API Setup (Required for Email Sync)

The system utilizes the Gmail API to dispatch preference request emails and poll for replies.

### Initial Setup
1. Enable the **Gmail API** in your Google Cloud Console.
2. Create an OAuth 2.0 client ID and download it as `credentials.json` to the project root.
3. Run the interactive authentication flow once to generate `token.json`:
   ```bash
   source venv/bin/activate
   python -c "from backend.email_service import get_gmail_service; get_gmail_service(server_mode=False)"
   ```
   A browser window will open to authorize the department Gmail account.
4. `token.json` is generated at the project root. The backend utilizes it for all subsequent API requests.

> **Docker Note:** `docker-compose.yml` mounts these token files. The token auto-refreshes (mounted writable) so the interactive flow does not need to be re-run unless access is revoked.

---

## System Capabilities

The backend provides a natural language interface to interact with the database and workflow tools:

- **Data Management:** Full CRUD operations for Professors, Courses, Timeslots, and Preferences.
- **Automated Workflow:**
  - **Poll & Extract:** The background worker polls the inbox. Replies are parsed into structured JSON via Vertex AI. High-confidence preferences (≥ 85%) without manual notes are flagged for auto-approval.
  - **Constraint Validation:** Preflight checks ensure the dataset is solvable before dispatching requests to AWS Lambda.
- **Solver Integration:** Invokes the OR-Tools optimization model asynchronously on AWS Lambda to prevent blocking the main FastAPI thread.
- **Schema Management:** Alembic handles zero-downtime schema migrations (`alembic upgrade head`).

---

## Project Structure

```text
backend/
  main.py          FastAPI application and background scheduler
  models.py        SQLAlchemy ORM models
  schemas.py       Pydantic validation schemas
  database.py      Database connection handling
  tools.py         Interface definitions for system actions
  email_service.py Gmail API integration
  ai.py            Vertex AI extraction logic
  solver.py        AWS Lambda invocation and payload construction
  alembic/         Database migration scripts
  routers/         FastAPI route handlers

frontend/
  src/
    app/           Next.js 16 App Router configuration
    lib/           API clients and shared TypeScript interfaces
    components/    React components, including the Dashboard and Chat Panel

lambda_solver/
  solver_core.py   Standalone OR-Tools scheduling logic for AWS Lambda deployment
  Dockerfile       Lambda container build definition
```

---

Copyright (c) 2026 Sameep Shah. All rights reserved.

No part of this source code may be used, copied, modified, merged, published,
distributed, sublicensed, or sold without the express prior written permission
of the copyright holder.

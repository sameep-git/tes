import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from . import models
from .database import engine
from .routers import health, professors, courses, schedules, preferences, chat, timeslots, insights, rooms
from .tools import trigger_poll_unread_replies


def run_migrations():
    """Run Alembic migrations programmatically to bring the DB to the latest version."""
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import inspect

    # Locate alembic.ini relative to this file (backend/main.py → backend/alembic.ini)
    backend_dir = Path(__file__).resolve().parent
    alembic_ini = backend_dir / "alembic.ini"

    if not alembic_ini.exists():
        print(f"[MIGRATIONS] alembic.ini not found at {alembic_ini}, falling back to create_all()")
        models.Base.metadata.create_all(bind=engine)
        return

    alembic_cfg = Config(str(alembic_ini))
    # Override the script_location to be absolute so it works regardless of cwd
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

    inspector = inspect(engine)
    if not inspector.has_table("alembic_version") and inspector.has_table("professors"):
        print("[MIGRATIONS] Existing database detected without alembic_version. Stamping head...")
        command.stamp(alembic_cfg, "head")
    else:
        print("[MIGRATIONS] Running alembic upgrade head...")
        command.upgrade(alembic_cfg, "head")
        
    print("[MIGRATIONS] Database is up to date.")

# Setup the background scheduler for automatic email polling
scheduler = BackgroundScheduler()

def scheduled_poll():
    print("Running automatic email poll...")
    try:
        # Use the full pipeline: poll → AI extract → auto-approve
        result = trigger_poll_unread_replies(server_mode=True)
        print(f"Auto email poll result: {result}")
    except RuntimeError as e:
        # get_gmail_service() raises RuntimeError in server_mode when the token
        # is missing or expired. Log clearly so the admin knows to re-authenticate.
        print(f"[EMAIL POLL] Auth error — run the app interactively to refresh token.json: {e}")
    except Exception as e:
        print(f"Error in automatic polling: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply migrations on startup (before the app starts serving)
    run_migrations()

    # Start the scheduler when the app starts
    # NOTE: This scheduler runs in-process. If the app is deployed with multiple
    # worker processes or replicas, each will poll the same inbox concurrently,
    # causing duplicate processing. Add a distributed lock (e.g. Redis SETNX)
    # or move polling to an external cron job before scaling beyond one worker.
    scheduler.add_job(scheduled_poll, 'interval', minutes=15)
    scheduler.start()
    print("Background email polling scheduler started (runs every 15 minutes).")
    yield
    # Shut down the scheduler when the app stops
    scheduler.shutdown()
    print("Background scheduler shut down.")

app = FastAPI(title="TES API", lifespan=lifespan)

# Setup CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(professors.router)
app.include_router(courses.router)
app.include_router(timeslots.router)
app.include_router(schedules.router)
app.include_router(preferences.router)
app.include_router(chat.router)
app.include_router(insights.router)
app.include_router(rooms.router)
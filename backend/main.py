from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from . import models
from .database import engine
from .routers import health, professors, courses, schedules, preferences, chat, timeslots, insights
from .tools import trigger_poll_unread_replies

# Create DB tables
models.Base.metadata.create_all(bind=engine)

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

# Setup CORS for the React frontend (running on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
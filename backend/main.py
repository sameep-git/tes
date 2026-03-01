from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from . import models
from .database import engine
from .routers import health, professors
from .email import poll_unread_replies

# Create DB tables
models.Base.metadata.create_all(bind=engine)

# Setup the background scheduler for automatic email polling
scheduler = BackgroundScheduler()

def scheduled_poll():
    print("Running automatic email poll...")
    try:
        replies = poll_unread_replies()
        if replies:
            print(f"Automatically processed {len(replies)} new replies!")
    except Exception as e:
        print(f"Error in automatic polling: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler when the app starts
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
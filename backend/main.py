from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import engine
from .routers import health, professors

# Create DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="TES API")

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
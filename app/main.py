# app/main.py
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import router as api_router
from app.database import engine
from app.models import Base

UI_FILE = Path(__file__).resolve().parent / "ui" / "index.html"

app = FastAPI(title="FitSense AI - Personalized Meal Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Ensure the database schema exists when the service starts.
Base.metadata.create_all(bind=engine)


@app.get("/", include_in_schema=False)
async def home():
    """Serve the single-page web app (app/ui/index.html)."""
    return FileResponse(UI_FILE, media_type="text/html")

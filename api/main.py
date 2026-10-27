"""Main FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .database import get_database
from .routers import admin, auth, members, meta, trainers

app = FastAPI(
    title="Gym Membership Management System API",
    description="Backend REST API for VIT BCSE302P Review 3 project (MongoDB + FastAPI + React)",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(members.router, prefix="/api")
app.include_router(trainers.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Gym Membership Management System API is running",
        "docs_url": "/docs",
        "health": "OK",
    }

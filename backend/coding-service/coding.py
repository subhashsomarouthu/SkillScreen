import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Allow imports from common-service (for logger, db, shared stuff)
sys.path.append("/common-service")

from controllers.coding_controller import router as execution_router
from controllers.questions_controller import router as questions_router
from controllers.sessions_controller import router as sessions_router

load_dotenv()

PORT = int(os.getenv("PORT", 8080))

app = FastAPI(
    title="Coding Service",
    description="Code execution, question management, and coding session tracking for interviews",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
# Existing execution endpoints (/, /health, /run, /evaluate)
app.include_router(execution_router)

# New question management endpoints (/v1/questions/...)
app.include_router(questions_router)

# New session management endpoints (/v1/sessions/...)
app.include_router(sessions_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    from db import DBFactory
    try:
        DBFactory.init()
        print("Database connection initialized")
    except Exception as e:
        print(f"Warning: Database connection failed: {e}")
        print("Some features (questions, sessions) will be unavailable")

"""
Legate FastAPI application entry point.
Registers all routers, middleware, and startup/shutdown hooks.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import auth, capsules, beneficiaries, checkin, settings, users
from app.api import activity

cfg = get_settings()

app = FastAPI(
    title="Legate API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

_dev_origins = [f"http://localhost:{p}" for p in range(5173, 5180)] + \
               [f"http://127.0.0.1:{p}" for p in range(5173, 5180)]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_dev_origins,  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(capsules.router, prefix="/capsules", tags=["capsules"])
app.include_router(beneficiaries.router, prefix="/beneficiaries", tags=["beneficiaries"])
app.include_router(checkin.router, prefix="/checkin", tags=["check-in"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(activity.router, prefix="/activity", tags=["activity"])


@app.get("/health", tags=["system"])
async def health_check():
    """Liveness probe endpoint."""
    return {"status": "ok"}

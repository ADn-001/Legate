"""
Legate FastAPI application entry point.
Registers all routers, middleware, and startup/shutdown hooks.
"""

import math
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.core.ratelimit import limiter
from app.api import auth, capsules, beneficiaries, checkin, settings, users
from app.api import activity, delivery

cfg = get_settings()

app = FastAPI(
    title="Legate API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    root_path=cfg.root_path,
)

def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom 429 handler that always includes Retry-After.

    slowapi's built-in handler injects Retry-After via request.state.view_rate_limit,
    but that attribute is None when the ASGI test transport processes the request
    (the state dict isn't propagated through the exception handler path in that case).
    We compute Retry-After from the window stats if available, falling back to 60 s
    (the longest rate-limit window in the app).
    """
    retry_after = 60
    try:
        vrl = getattr(request.state, "view_rate_limit", None)
        if vrl is not None:
            reset_time = vrl[1].reset_time
            retry_after = max(1, math.ceil(reset_time - time.time()))
    except Exception:
        pass
    response = JSONResponse(
        {"detail": f"Rate limit exceeded: {exc.detail}"},
        status_code=429,
    )
    response.headers["Retry-After"] = str(retry_after)
    return response


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Must be added AFTER CORSMiddleware so CORS runs first (outermost) and
# rate-limited 429 responses still carry CORS headers.
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(capsules.router, prefix="/capsules", tags=["capsules"])
app.include_router(beneficiaries.router, prefix="/beneficiaries", tags=["beneficiaries"])
app.include_router(checkin.router, prefix="/checkin", tags=["check-in"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(activity.router, prefix="/activity", tags=["activity"])
app.include_router(delivery.router, prefix="/delivery", tags=["delivery"])


@app.get("/health", tags=["system"])
async def health_check():
    """Liveness probe endpoint — exempt from rate limiting."""
    return {"status": "ok"}

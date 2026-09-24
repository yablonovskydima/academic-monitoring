from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from auth_service.bootstrap import bootstrap_admin
from auth_service.config import AUTH_SERVICE_PORT
from auth_service.controllers import auth, audit_log, curator_assignments, dean_assignments, users
from auth_service.database import SessionLocal, init_db
from auth_service.rate_limit import RateLimitExceeded


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    db = SessionLocal()
    try:
        bootstrap_admin(db)
    finally:
        db.close()

    yield

app = FastAPI(title="Auth Service", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(curator_assignments.router)
app.include_router(dean_assignments.router)
app.include_router(audit_log.router)


@app.exception_handler(RateLimitExceeded)
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry_after = int(exc.retry_after) + 1
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
        headers={"Retry-After": str(retry_after)},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    uvicorn.run("auth_service.main:app", host="0.0.0.0", port=AUTH_SERVICE_PORT, reload=True)


if __name__ == "__main__":
    run()

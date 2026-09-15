from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from auth_service.config import AUTH_SERVICE_PORT
from auth_service.controllers import auth
from auth_service.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Auth Service", lifespan=lifespan)
app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    uvicorn.run("auth_service.main:app", host="0.0.0.0", port=AUTH_SERVICE_PORT, reload=True)


if __name__ == "__main__":
    run()

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from ml_service.controllers import health
from ml_service.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="ML Service")
app.include_router(health.router)

@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    uvicorn.run("ml_service.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    run()
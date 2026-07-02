from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from import_service.controllers import students
from import_service.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
app = FastAPI(title="Import Service", lifespan=lifespan)
app.include_router(students.router)

@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    uvicorn.run("import_service.main:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    run()
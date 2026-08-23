from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from import_service.controllers import (
    students, groups, teachers, semesters, subjects,
    subject_offerings, class_sessions, student_features,
)
from import_service.config import IMPORT_SERVICE_PORT
from import_service.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Import Service", lifespan=lifespan)
app.include_router(students.router)
app.include_router(groups.router)
app.include_router(teachers.router)
app.include_router(semesters.router)
app.include_router(subjects.router)
app.include_router(subject_offerings.router)
app.include_router(class_sessions.router)
app.include_router(student_features.router)

@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    uvicorn.run("import_service.main:app", host="0.0.0.0", port=IMPORT_SERVICE_PORT, reload=True)


if __name__ == "__main__":
    run()
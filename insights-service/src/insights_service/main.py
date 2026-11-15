from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from insights_service.config import INSIGHTS_SERVICE_PORT
from insights_service.controllers import group_summaries, insight_changes, insight_runs, student_insights
from insights_service.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Insights Service", lifespan=lifespan)
app.include_router(insight_runs.router)
app.include_router(student_insights.router)
app.include_router(insight_changes.router)
app.include_router(group_summaries.router)


@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    uvicorn.run("insights_service.main:app", host="0.0.0.0", port=INSIGHTS_SERVICE_PORT, reload=True)


if __name__ == "__main__":
    run()

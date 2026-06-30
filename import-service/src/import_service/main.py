import uvicorn
from fastapi import FastAPI

from import_service.controllers import students

app = FastAPI(title="Import Service")

app.include_router(students.router)


@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    uvicorn.run("import_service.main:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    run()
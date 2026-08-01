import uvicorn


from fastapi import FastAPI

app = FastAPI(title="ML Service")

@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    uvicorn.run("ml_service.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    run()
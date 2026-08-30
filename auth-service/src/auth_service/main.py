import uvicorn
from auth_service.config import AUTH_SERVICE_PORT


def run():
    uvicorn.run("ml_service.main:app", host="0.0.0.0", port=AUTH_SERVICE_PORT, reload=True)


if __name__ == "__main__":
    run()
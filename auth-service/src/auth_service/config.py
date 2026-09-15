import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

AUTH_SERVICE_PORT = int(os.getenv("AUTH_SERVICE_PORT", "8003"))

IMPORT_SERVICE_URL = os.getenv("IMPORT_SERVICE_URL")

if not IMPORT_SERVICE_URL:
    raise RuntimeError("IMPORT_SERVICE_URL is not set. Check your .env file.")

REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set. Check your .env file.")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
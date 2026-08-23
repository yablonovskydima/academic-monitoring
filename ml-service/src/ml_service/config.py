import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

IMPORT_SERVICE_URL = os.getenv("IMPORT_SERVICE_URL")

if not IMPORT_SERVICE_URL:
    raise RuntimeError("IMPORT_SERVICE_URL is not set. Check your .env file.")

KEEP_INACTIVE_MODEL_VERSIONS = int(os.getenv("KEEP_INACTIVE_MODEL_VERSIONS", "5"))

ML_SERVICE_PORT = int(os.getenv("ML_SERVICE_PORT", "8002"))
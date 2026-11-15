import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

IMPORT_SERVICE_URL = os.getenv("IMPORT_SERVICE_URL")

if not IMPORT_SERVICE_URL:
    raise RuntimeError("IMPORT_SERVICE_URL is not set. Check your .env file.")

INSIGHTS_SERVICE_URL = os.getenv("INSIGHTS_SERVICE_URL")

KEEP_INACTIVE_MODEL_VERSIONS = int(os.getenv("KEEP_INACTIVE_MODEL_VERSIONS", "5"))

ML_SERVICE_PORT = int(os.getenv("ML_SERVICE_PORT", "8002"))

ADMISSION_ABSENCE_THRESHOLD = float(os.getenv("ADMISSION_ABSENCE_THRESHOLD", "75"))
ADMISSION_GRADE_THRESHOLD = float(os.getenv("ADMISSION_GRADE_THRESHOLD", "50"))
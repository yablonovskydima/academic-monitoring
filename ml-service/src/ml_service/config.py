import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

IMPORT_SERVICE_URL = os.getenv("IMPORT_SERVICE_URL")

if not IMPORT_SERVICE_URL:
    raise RuntimeError("IMPORT_SERVICE_URL is not set. Check your .env file.")
import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

IMPORT_SERVICE_PORT = int(os.getenv("IMPORT_SERVICE_PORT", "8001"))

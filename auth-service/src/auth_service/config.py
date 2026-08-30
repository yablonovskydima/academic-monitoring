import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

AUTH_SERVICE_PORT = int(os.getenv("AUTH_SERVICE_PORT", "8003"))
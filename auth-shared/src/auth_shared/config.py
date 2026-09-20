import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set. Check your .env file.")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

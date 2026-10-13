"""Settings, read from environment variables.

Locally they come from backend/.env (a copy of .env.example); on Render they are set in its dashboard.
Secrets have no default on purpose: the app refuses to start without them.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env if it exists. A variable that is already set in the real environment wins.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is not set (see backend/.env.example).")
    return value


DATABASE_URL = _required("DATABASE_URL")
JWT_SECRET = _required("JWT_SECRET")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))
# Browser origins allowed to call the API, e.g. "http://localhost:5173,https://my-app.vercel.app".
CORS_ORIGINS = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",") if origin.strip()]

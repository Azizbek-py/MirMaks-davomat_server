from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"')
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().strip('"')
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
ADMIN_IDS = [int(value.strip()) for value in os.getenv("ADMIN_IDS", "").split(",") if value.strip()]
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip().strip('"')
HOST = os.getenv("HOST", "0.0.0.0").strip()
PORT = int(os.getenv("PORT", "8000"))
OFFICE_LAT = float(os.getenv("OFFICE_LAT", "0"))
OFFICE_LON = float(os.getenv("OFFICE_LON", "0"))
OFFICE_RADIUS = float(os.getenv("OFFICE_RADIUS", "100"))
MAX_SUBMIT_SECONDS = int(os.getenv("MAX_SUBMIT_SECONDS", "15"))
ALLOW_DUPLICATE_ATTENDANCE = os.getenv("ALLOW_DUPLICATE_ATTENDANCE", "false").lower() == "true"
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads")
DB_PATH = os.getenv("DB_PATH", "db/tinydb.json")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
TIMEZONE = os.getenv("TIMEZONE", "UTC").strip()

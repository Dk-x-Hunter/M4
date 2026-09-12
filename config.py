import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = Path(os.getenv("DB_FILE", BASE_DIR / "data.db"))

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SESSION_STRING = os.getenv("SESSION_STRING", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

SUDO_USERS = []
for value in os.getenv("SUDO_USERS", "").split(","):
    value = value.strip()
    if value:
        try:
            SUDO_USERS.append(int(value))
        except ValueError:
            pass

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MAX_QUEUE_SIZE = max(1, int(os.getenv("MAX_QUEUE_SIZE", "50")))
PROMOTION_INTERVAL = max(5, int(os.getenv("PROMOTION_INTERVAL", "15")))

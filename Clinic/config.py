# Smart Clinic Kiosk - Configuration Module
# ASCII only file.

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def _try_load_env_file(path):
    if load_dotenv is None:
        return
    try:
        if path.exists():
            load_dotenv(str(path), override=False)
    except Exception:
        pass


def _load_env_files():
    here = Path(__file__).resolve().parent
    candidates = [
        Path.cwd() / ".env",
        here / ".env",
        here.parent / ".env",
        here.parent / "medication_sys" / ".env",
        here.parent / "Clinic" / ".env",
    ]
    for path in candidates:
        _try_load_env_file(path)


_load_env_files()

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN") or os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("BASE_ID") or os.getenv("AIRTABLE_BASE_ID")

TABLE_AVAILABLE_STOCK = "Available Stock"
TABLE_DISPENSED_HISTORY = "History"
TABLE_SYSTEM_USERS = "Users"
TABLE_PATIENTS = "Patients"

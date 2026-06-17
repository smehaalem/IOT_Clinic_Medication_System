# ==========================================
# Smart Clinic Kiosk - Configuration Module
# ==========================================

import os
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = "apptm9srPy0J7Z5Hc"


TABLE_AVAILABLE_STOCK = "Available Stock"
TABLE_DISPENSED_HISTORY = "History"
TABLE_SYSTEM_USERS = "Users"
# ==========================================
# Smart Clinic Kiosk - Configuration Module
# ==========================================

import os
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = os.getenv("BASE_ID")


TABLE_AVAILABLE_STOCK = "Available Stock"
TABLE_DISPENSED_HISTORY = "History"
TABLE_SYSTEM_USERS = "Users"
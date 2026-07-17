"""
Airtable API layer with emergency offline-first support for medicines.

The rest of the GUI can keep calling airtable_api.stock_table / functions here.
This file now writes medicine changes to SQLite first, then tries Airtable.
If Airtable is unavailable, the operation is saved in a local sync queue.
"""

import random
import re
from datetime import datetime

try:
    from pyairtable import Api
except Exception as import_error:
    Api = None
    print(f"pyairtable is not available. Cloud mode disabled: {import_error}")

import config
import local_db
import sync_manager


local_db.init_db()

cloud_airtable_api = None
cloud_stock_table = None
cloud_history_table = None
cloud_catalog_table = None
users_table = None
mock_patients_table = None


# =====================================================================
# Cloud initialization
# =====================================================================
try:
    if Api is None:
        raise RuntimeError("pyairtable package is not installed")
    cloud_airtable_api = Api(config.AIRTABLE_TOKEN)
    cloud_stock_table = cloud_airtable_api.table(config.BASE_ID, config.TABLE_AVAILABLE_STOCK)
    cloud_history_table = cloud_airtable_api.table(config.BASE_ID, config.TABLE_DISPENSED_HISTORY)

    catalog_table_name = getattr(
        config,
        "TABLE_MEDICINES_CATALOG",
        "Medicines Catalog"
    )
    cloud_catalog_table = cloud_airtable_api.table(
        config.BASE_ID,
        catalog_table_name
    )

    users_table = cloud_airtable_api.table(config.BASE_ID, config.TABLE_SYSTEM_USERS)
    mock_patients_table = cloud_airtable_api.table(config.BASE_ID, config.TABLE_SYSTEM_MOCK)
    print("Airtable cloud connection object initialized.")
except Exception as e:
    print(f"Error initializing Airtable connection object: {e}")


# =====================================================================
# Safe value extraction helpers
# =====================================================================
def safe_extract(value, target_type=str):
    if value is None:
        return 0 if target_type == int else ""

    if isinstance(value, list):
        value = value[0] if value else (0 if target_type == int else "")

    if isinstance(value, dict):
        value = value.get("text", value.get("value", 0 if target_type == int else ""))

    try:
        if target_type == int:
            clean_str = str(value).split(".")[0].strip()
            return int(clean_str) if clean_str else 0
        return str(value).strip()
    except (ValueError, TypeError):
        return 0 if target_type == int else str(value).strip()


def clean_barcode_value(value):
    """Return the real scanner barcode and ignore Airtable record IDs/placeholders."""
    if value is None:
        return ""

    values = value if isinstance(value, list) else [value]
    for current in values:
        if isinstance(current, dict):
            current = current.get("text") or current.get("value") or current.get("name") or ""
        text = str(current).strip()
        low = text.lower()

        if low in ("", "none", "null", "nan", "barcode", "no_barcode", "n/a"):
            continue
        if low.startswith("rec") and len(text) >= 10:
            continue
        return text

    return ""


def extract_real_barcode(fields):
    """Extract barcode from all field names used by this Airtable base."""
    fields = fields or {}
    candidates = [
        fields.get("Search key (auto 12)"),
        fields.get("Barcode (from Barcode)"),
        fields.get("Barcode lookup"),
        fields.get("Barcode"),
    ]
    for candidate in candidates:
        clean = clean_barcode_value(candidate)
        if clean:
            return clean
    return ""


def _record_fields(record):
    if hasattr(record, "fields"):
        return dict(record.fields or {})
    if isinstance(record, dict):
        return dict(record.get("fields", {}) or {})
    return {}


def _record_id(record):
    if hasattr(record, "id"):
        return record.id
    if isinstance(record, dict):
        return record.get("id") or record.get("record_id")
    return None


def _cloud_available():
    return cloud_stock_table is not None and sync_manager.has_internet()


def _history_cloud_available():
    return cloud_history_table is not None and sync_manager.has_internet()


def _looks_like_local_id(record_id):
    return local_db.is_local_id(record_id)


def _filter_local_stock_records(formula=None):
    """Very small Airtable formula fallback for the formulas used in this project."""
    if not formula:
        return local_db.get_all_medicine_records()

    text = str(formula).strip()

    lower_name_match = re.search(r"LOWER\(\{Medicine Name\}\)\s*=\s*LOWER\('(.+)'\)", text)
    if lower_name_match:
        return local_db.find_medicines_by_name_exact(lower_name_match.group(1))

    exact_match = re.search(r"\{([^}]+)\}\s*=\s*'(.+)'", text)
    if exact_match:
        field_name = exact_match.group(1).strip()
        value = exact_match.group(2).strip()
        if field_name in ("Barcode", "Barcode lookup", "Barcode (from Barcode)", "Search key (auto 12)"):
            return local_db.find_medicines_by_barcode(value)
        if field_name == "Medicine Name":
            return local_db.find_medicines_by_name_exact(value)

    # Unknown formula: return all local records rather than crashing the UI.
    return local_db.get_all_medicine_records()


# =====================================================================
# Hybrid table wrappers
# =====================================================================
class HybridStockTable:
    def __init__(self, cloud_table):
        self.cloud_table = cloud_table

    def all(self, formula=None, **kwargs):
        if self.cloud_table is not None and sync_manager.has_internet():
            try:
                sync_pending_operations(silent=True)
                if formula is not None:
                    records = self.cloud_table.all(formula=formula, **kwargs)
                else:
                    records = self.cloud_table.all(**kwargs)
                for record in records:
                    local_db.upsert_medicine_record(record, dirty=0)
                return records
            except Exception as e:
                print(f"Cloud stock fetch failed, using local SQLite: {e}")

        return _filter_local_stock_records(formula)

    def get(self, record_id, **kwargs):
        if self.cloud_table is not None and sync_manager.has_internet() and not _looks_like_local_id(record_id):
            try:
                record = self.cloud_table.get(record_id, **kwargs)
                if record:
                    local_db.upsert_medicine_record(record, dirty=0)
                return record
            except Exception as e:
                print(f"Cloud stock get failed, using local SQLite: {e}")

        return local_db.get_medicine_record(record_id)

    def create(self, fields, typecast=True, **kwargs):
        fields = dict(fields or {})
        if self.cloud_table is not None and sync_manager.has_internet():
            try:
                sync_pending_operations(silent=True)
                created = self.cloud_table.create(fields, typecast=typecast, **kwargs)
                local_db.upsert_medicine_record(created, dirty=0)
                return created
            except Exception as e:
                print(f"Cloud stock create failed, saving locally: {e}")

        local_record = local_db.create_local_medicine(fields, dirty=1)
        local_db.enqueue_operation("ADD_MEDICINE", local_record["id"], {"fields": fields})
        return local_record

    def update(self, record_id, fields, typecast=True, **kwargs):
        fields = dict(fields or {})
        local_record = local_db.update_medicine_fields(record_id, fields, dirty=1)

        if self.cloud_table is not None and sync_manager.has_internet() and not _looks_like_local_id(record_id):
            try:
                sync_pending_operations(silent=True)
                updated = self.cloud_table.update(record_id, fields, typecast=typecast, **kwargs)
                local_db.upsert_medicine_record(updated, dirty=0)
                return updated
            except Exception as e:
                print(f"Cloud stock update failed, queued for sync: {e}")

        op_type = "UPDATE_MEDICINE_QUANTITY" if set(fields.keys()) == {"Current Pills Count"} else "UPDATE_MEDICINE_FIELDS"
        local_db.enqueue_operation(op_type, record_id, {"fields": fields})
        return local_record

    def delete(self, record_id, **kwargs):
        local_db.delete_medicine_record(record_id, dirty=1)
        if self.cloud_table is not None and sync_manager.has_internet() and not _looks_like_local_id(record_id):
            try:
                sync_pending_operations(silent=True)
                self.cloud_table.delete(record_id, **kwargs)
                return True
            except Exception as e:
                print(f"Cloud stock delete failed, queued for sync: {e}")

        local_db.enqueue_operation("DELETE_MEDICINE", record_id, {})
        return True


class HybridHistoryTable:
    def __init__(self, cloud_table):
        self.cloud_table = cloud_table

    def create(self, fields, typecast=True, **kwargs):
        fields = dict(fields or {})
        local_history_id = local_db.add_local_history(
            fields.get("Action Type", ""),
            fields.get("Barcode", ""),
            fields.get("Action By User", ""),
            fields.get("Quantity", 0),
            fields.get("Removal Reason", ""),
            fields.get("Doctor", ""),
            synced=0,
        )

        if self.cloud_table is not None and sync_manager.has_internet():
            try:
                sync_pending_operations(silent=True)
                created = self.cloud_table.create(fields, typecast=typecast, **kwargs)
                return created
            except Exception as e:
                print(f"Cloud history create failed, queued for sync: {e}")

        local_db.enqueue_operation("LOG_TRANSACTION", str(local_history_id), {"fields": fields})
        return {"id": f"local_history_{local_history_id}", "fields": fields}

    def all(self, **kwargs):
        if self.cloud_table is not None and sync_manager.has_internet():
            try:
                return self.cloud_table.all(**kwargs)
            except Exception as e:
                print(f"Cloud history fetch failed: {e}")
        return []


stock_table = HybridStockTable(cloud_stock_table)
history_table = HybridHistoryTable(cloud_history_table)


# =====================================================================
# Patient mock table function - stays online only by request
# =====================================================================
def assign_mock_data_to_patient(new_patient_id):
    try:
        if mock_patients_table is None:
            raise RuntimeError("Mock patients table is not initialized")
        formula = "{Personal ID} = '0'"
        available_records = mock_patients_table.all(formula=formula)
        if not available_records:
            print("No available mock records left with Personal ID = '0'.")
            return None
        chosen_record = random.choice(available_records)
        record_id = chosen_record["id"] if isinstance(chosen_record, dict) else chosen_record.id
        updated_record = mock_patients_table.update(record_id, {"Personal ID": str(new_patient_id)})
        return _record_fields(updated_record)
    except Exception as e:
        print(f"Error assigning mock data in Airtable: {e}")
        raise e


# =====================================================================
# Medicines Catalog synchronization
# =====================================================================
def _escape_airtable_formula_text(value):
    return str(value or "").replace("\\", "\\\\").replace("'", "\\'")


def sync_medicine_to_catalog(
    medicine_name,
    barcode,
    category="",
    strength=""
):
    """
    Create or update the matching Medicines Catalog row.

    The low-stock report reads the medicine display name from the catalog's
    "Name" field. New stock rows are therefore mirrored into the catalog so
    they do not appear as Unknown.
    """
    if cloud_catalog_table is None or not sync_manager.has_internet():
        return None

    clean_name = str(medicine_name or "").strip()
    clean_barcode = clean_barcode_value(barcode)
    clean_category = str(category or "").strip()
    clean_strength = str(strength or "").strip()

    if not clean_name:
        return None

    try:
        matching_records = []

        # Prefer matching by the real barcode.
        if clean_barcode:
            escaped_barcode = _escape_airtable_formula_text(clean_barcode)
            try:
                matching_records = cloud_catalog_table.all(
                    formula=f"{{Barcode}} = '{escaped_barcode}'"
                )
            except Exception:
                matching_records = []

        # Fall back to the medicine name when there is no usable barcode.
        if not matching_records:
            escaped_name = _escape_airtable_formula_text(clean_name)
            try:
                matching_records = cloud_catalog_table.all(
                    formula=f"LOWER({{Name}}) = LOWER('{escaped_name}')"
                )
            except Exception:
                matching_records = []

        catalog_fields = {
            "Name": clean_name,
        }

        if clean_barcode:
            catalog_fields["Barcode"] = clean_barcode

        if clean_category:
            catalog_fields["Category / Use"] = clean_category

        if clean_strength:
            catalog_fields["Strength"] = clean_strength

        if matching_records:
            record = matching_records[0]
            record_id = _record_id(record)
            return cloud_catalog_table.update(
                record_id,
                catalog_fields,
                typecast=True
            )

        return cloud_catalog_table.create(
            catalog_fields,
            typecast=True
        )

    except Exception as error:
        # Catalog synchronization must never block stock operations.
        print(f"Catalog synchronization failed: {error}")
        return None


# =====================================================================
# Available Stock functions
# =====================================================================
def get_all_medications():
    return stock_table.all()


def find_medication_by_barcode(barcode_value):
    try:
        records = get_all_medications_by_barcode(barcode_value)
        return records[0] if records else None
    except Exception as e:
        print(f"Error searching medication by barcode: {e}")
        return None


def get_all_medications_by_barcode(barcode_value):
    try:
        requested_barcode = clean_barcode_value(barcode_value)
        if not requested_barcode:
            return []

        # Do not rely on Airtable formula here. In this base, the displayed field
        # "Barcode" can be a linked-record id, while the real scanner value is in
        # "Barcode (from Barcode)" or "Search key (auto 12)".
        records = stock_table.all()
        matched = []
        for record in records:
            fields = _record_fields(record)
            if extract_real_barcode(fields) == requested_barcode:
                matched.append(record)
        return matched
    except Exception as e:
        print(f"Error searching medications by barcode: {e}")
        return []


def find_all_batches_by_barcode(barcode):
    try:
        requested_barcode = clean_barcode_value(barcode)
        if not requested_barcode:
            return []

        records = get_all_medications_by_barcode(requested_barcode)
        batches = []
        for r in records:
            fields = _record_fields(r)
            rec_id = _record_id(r)

            if extract_real_barcode(fields) != requested_barcode:
                continue

            qty = safe_extract(fields.get("Current Pills Count"), int)
            if qty <= 0:
                continue
            batches.append({
                "id": rec_id,
                "medicine_name": safe_extract(fields.get("Medicine Name"), str),
                "expiry_date": safe_extract(fields.get("Expiry Date"), str) if fields.get("Expiry Date") else "9999-12-31",
                "current_quantity": qty,
                "batch_number": safe_extract(fields.get("A Batch") or fields.get("Batch Number"), str),
            })
        batches.sort(key=lambda x: x["expiry_date"])
        return batches
    except Exception as e:
        print(f"Error fetching batches: {e}")
        return []


def add_new_medication(medicine_name, barcode, active_ingredient, dosage, expiry_date,
                       initial_pills, current_pills, batch_number, category, user_record_id=None):
    try:
        fields_data = {
            "Medicine Name": str(medicine_name),
            "Barcode": str(barcode),
            "Active Ingredient": str(active_ingredient),
            "Dosage": str(dosage),
            "Expiry Date": str(expiry_date),
            "Initial Pills Count": int(initial_pills),
            "Current Pills Count": int(current_pills),
            "A Batch": str(batch_number),
            "Category": str(category),
        }
        if user_record_id:
            fields_data["USER"] = [str(user_record_id)]
        new_record = stock_table.create(fields_data, typecast=True)

        sync_medicine_to_catalog(
            medicine_name=medicine_name,
            barcode=barcode,
            category=category,
            strength=dosage
        )

        print(f"Added medication locally/cloud: {medicine_name}")
        return new_record
    except Exception as e:
        print(f"Error adding new medication: {e}")
        return None


def update_medication_quantity(record_id, new_pill_count):
    try:
        fields_to_update = {"Current Pills Count": int(new_pill_count)}
        updated_record = stock_table.update(record_id, fields_to_update, typecast=True)
        print(f"Updated local stock count. Current Pills: {new_pill_count}")
        return updated_record
    except Exception as e:
        print(f"Error updating medication quantity: {e}")
        return None


def update_medication_full_fields(record_id, medicine_name, barcode, active_ingredient, dosage, expiry_date,
                                  pills_count, batch_number, cat, new_initial_count=None):
    try:
        fields_to_update = {
            "Medicine Name": str(medicine_name),
            "Barcode": str(barcode),
            "Active Ingredient": str(active_ingredient),
            "Dosage": str(dosage),
            "Expiry Date": str(expiry_date),
            "Current Pills Count": int(pills_count),
            "A Batch": str(batch_number),
            "A Category": str(cat),
        }
        if new_initial_count is not None:
            fields_to_update["Initial Pills Count"] = int(new_initial_count)
        updated_record = stock_table.update(record_id, fields_to_update, typecast=True)

        sync_medicine_to_catalog(
            medicine_name=medicine_name,
            barcode=barcode,
            category=cat,
            strength=dosage
        )

        print(f"Updated medication record: {record_id}")
        return updated_record
    except Exception as e:
        print(f"Error updating medication: {e}")
        return None


def delete_medication_record(record_id):
    try:
        return bool(stock_table.delete(record_id))
    except Exception as e:
        print(f"Error deleting medication: {e}")
        return False


# =====================================================================
# System Users functions - cloud first, local cache fallback
# =====================================================================
def get_all_users():
    try:
        if users_table is not None and sync_manager.has_internet():
            records = users_table.all()
            user_list = []
            for record in records:
                fields = _record_fields(record)
                rec_id = _record_id(record)
                user_data = {
                    "record_id": rec_id,
                    "Username": safe_extract(fields.get("Username"), str),
                    "Password": safe_extract(fields.get("Password"), str),
                    "Role": safe_extract(fields.get("Role"), str),
                    "PIN Code": safe_extract(fields.get("PIN Code"), str),
                    "Full Name": safe_extract(fields.get("Full Name"), str),
                    "Email": safe_extract(fields.get("Email"), str),
                }
                user_list.append(user_data)
            local_db.cache_users(user_list)
            return user_list
    except Exception as e:
        print(f"Cloud users fetch failed, using local cache: {e}")

    return local_db.get_cached_users()


def add_new_user(username, password, role, pin_code, full_name, email=""):
    try:
        if users_table is None:
            raise RuntimeError("Users table is not initialized")
        fields_data = {
            "Username": str(username).strip(),
            "Password": str(password).strip(),
            "Role": str(role).strip(),
            "PIN Code": str(pin_code).strip(),
            "Full Name": str(full_name).strip(),
            "Email": str(email).strip(),
            "Last Login": "",
        }
        return users_table.create(fields_data, typecast=True)
    except Exception as e:
        print(f"Error adding new user to cloud: {e}")
        return None


def update_user_records(record_id, username, password, role, pin_code, full_name):
    try:
        if users_table is None:
            raise RuntimeError("Users table is not initialized")
        fields_to_update = {
            "Username": str(username).strip(),
            "Password": str(password).strip(),
            "Role": str(role).strip(),
            "PIN Code": str(pin_code).strip(),
            "Full Name": str(full_name).strip(),
        }
        return users_table.update(record_id, fields_to_update, typecast=True)
    except Exception as e:
        print(f"Error updating user in cloud: {e}")
        return None


def delete_user_record(record_id):
    try:
        if users_table is None:
            raise RuntimeError("Users table is not initialized")
        users_table.delete(record_id)
        return True
    except Exception as e:
        print(f"Error deleting user from cloud: {e}")
        return False


def authenticate_user(username, password):
    try:
        all_users = get_all_users()
        for user in all_users:
            if str(user.get("Username", "")).strip().lower() == str(username).strip().lower():
                db_password = safe_extract(user.get("Password"), str)
                if db_password == str(password).strip():
                    return safe_extract(user.get("Role"), str)
        return None
    except Exception as e:
        print(f"Error during authentication: {e}")
        return None


# =====================================================================
# History functions
# =====================================================================
def log_transaction(action_type, barcode, action_by_user, quantity_taken, removal_reason="", doctor_name=""):
    try:
        fields_data = {
            "Action Type": str(action_type),
            "Barcode": str(barcode),
            "Action By User": str(action_by_user),
            "Quantity": int(quantity_taken),
            "Doctor": str(doctor_name),
        }
        if removal_reason:
            fields_data["Removal Reason"] = [str(removal_reason)]
        return history_table.create(fields_data, typecast=True)
    except Exception as e:
        print(f"Error logging transaction: {e}")
        return None


def get_all_history():
    try:
        return history_table.all()
    except Exception as e:
        print(f"Error fetching transaction history: {e}")
        return []


# =====================================================================
# Sync public helpers for GUI button / startup
# =====================================================================
def sync_pending_operations(silent=False):
    success, failed = sync_manager.sync_pending_changes(
        cloud_stock_table=cloud_stock_table,
        cloud_history_table=cloud_history_table,
    )
    if not silent:
        print(f"Sync completed. success={success}, failed_or_pending={failed}")
    return success, failed


def get_pending_sync_count():
    return local_db.pending_count()


def is_cloud_online():
    return sync_manager.has_internet(force=True)


def refresh_local_stock_from_cloud():
    """Manual full stock download from Airtable into SQLite."""
    if cloud_stock_table is None or not sync_manager.has_internet(force=True):
        return 0
    records = cloud_stock_table.all()
    for record in records:
        local_db.upsert_medicine_record(record, dirty=0)
    return len(records)

def warm_up_offline_cache(sync_stock=True, sync_users=True):
    """
    Preload cloud data into SQLite while internet exists.
    This is important because the kiosk must be able to log in later while offline.
    Returns a small report dictionary for debug prints.
    """
    report = {"online": False, "users_cached": 0, "medicines_cached": 0, "error": ""}
    try:
        report["online"] = is_cloud_online()
        if not report["online"]:
            return report

        if sync_users:
            users = get_all_users()
            report["users_cached"] = len(users or [])

        if sync_stock:
            report["medicines_cached"] = refresh_local_stock_from_cloud()

    except Exception as exc:
        report["error"] = str(exc)

    return report


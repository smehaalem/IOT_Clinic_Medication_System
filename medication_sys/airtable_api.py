import sys
import os
from datetime import datetime

from pyairtable import Api
import config

# Initialize connection to the Airtable API cloud
try:
    airtable_api = Api(config.AIRTABLE_TOKEN)

    # Establish direct references to the database tables
    stock_table = airtable_api.table(config.BASE_ID, config.TABLE_AVAILABLE_STOCK)
    history_table = airtable_api.table(config.BASE_ID, config.TABLE_DISPENSED_HISTORY)
    users_table = airtable_api.table(config.BASE_ID, config.TABLE_SYSTEM_USERS)

    print("🌍 Airtable cloud connection successfully initialized!")
except Exception as e:
    print(f"❌ Error initializing Airtable connection: {e}")


# =====================================================================
# 🛡️ SMART SAFE EXTRACTOR HUB (الدالة العبقرية لحماية وفك جميع حقول السيرفر)
# =====================================================================

def safe_extract(value, target_type=str):
    """
    تفكك أي قيمة قادمة من Airtable بأمان أياً كان شكلها لتفادي كراش القواميس واللستات.
    تدعم تنظيف حقول مثل {'text': '128'} أو ['450mg'] وتحويلها لنص أو رقم صحيح.
    """
    if value is None:
        return 0 if target_type == int else ""

    # 1. إذا كانت القيمة مصفوفة/لستة، نأخذ العنصر الأول منها
    if isinstance(value, list):
        value = value[0] if value else (0 if target_type == int else "")

    # 2. إذا كانت القيمة دكشنري/قاموس مثل {'text': '128'}، نسحب القيمة الداخلية
    if isinstance(value, dict):
        value = value.get('text', value.get('value', 0 if target_type == int else ""))

    # 3. التحويل النهائي للنوع المطلوب مع التنظيف
    try:
        if target_type == int:
            # تنظيف النص من أي نقاط عشرية أو فراغات قبل التحويل لرقم
            clean_str = str(value).split('.')[0].strip()
            return int(clean_str) if clean_str else 0
        else:
            return str(value).strip()
    except (ValueError, TypeError):
        return 0 if target_type == int else str(value).strip()


# =====================================================================
# 📦 AVAILABLE STOCK TABLE FUNCTIONS
# =====================================================================

def get_all_medications():
    """
    Fetches the entire list of medications stored in the cloud stock table.
    """
    try:
        records = stock_table.all()
        return records
    except Exception as e:
        print(f"❌ Error fetching medication stock: {e}")
        return []


def find_medication_by_barcode(barcode_value):
    """
    Searches for a specific medication in the cloud based on its unique barcode.
    """
    try:
        formula = f"{{Barcode}} = '{barcode_value}'"
        records = stock_table.all(formula=formula)
        if records:
            return records[0]
        return None
    except Exception as e:
        print(f"❌ Error searching medication by barcode: {e}")
        return None


def get_all_medications_by_barcode(barcode_value):
    """
    Searches for ALL medication records in the cloud based on a unique barcode.
    """
    try:
        formula = f"{{Barcode}} = '{barcode_value}'"
        records = stock_table.all(formula=formula)
        return records
    except Exception as e:
        print(f"❌ Error searching medications by barcode: {e}")
        return []


def find_all_batches_by_barcode(barcode):
    """
    Returns all active batches for a specific barcode using the super safe extractor.
    """
    try:
        records = stock_table.all()
        batches = []

        for r in records:
            fields = r.fields if hasattr(r, 'fields') else r.get('fields', {})
            rec_id = r.id if hasattr(r, 'id') else r.get('id')

            # حماية وفك باركود اللوك أب الموجه من السيرفر
            lookup_value = safe_extract(fields.get("Barcode lookup"), str)

            if lookup_value != str(barcode).strip():
                continue

            # حماية وفك حقل الكمية الرقمي
            qty = safe_extract(fields.get("Current Pills Count"), int)
            if qty <= 0:
                continue

            batches.append({
                "id": rec_id,
                "medicine_name": safe_extract(fields.get("Medicine Name"), str),
                "expiry_date": safe_extract(fields.get("Expiry Date"), str) if fields.get(
                    "Expiry Date") else "9999-12-31",
                "current_quantity": qty,
                "batch_number": safe_extract(fields.get("A Batch"), str)
            })

        batches.sort(key=lambda x: x["expiry_date"])
        return batches

    except Exception as e:
        print(f"❌ Error fetching all batches securely: {e}")
        return []


def add_new_medication(medicine_name, barcode, active_ingredient, dosage, expiry_date,
                       initial_pills, current_pills, batch_number, user_record_id=None):
    """
    Creates a new medication record in the Available_Stock table.
    """
    try:
        fields_data = {
            "Medicine Name": str(medicine_name),
            "Barcode": str(barcode),
            "Active Ingredient": str(active_ingredient),
            "Dosage": str(dosage),
            "Expiry Date": str(expiry_date),
            "Initial Pills Count": int(initial_pills),
            "Current Pills Count": int(current_pills),
            "A Batch": str(batch_number)
        }

        if user_record_id:
            fields_data["USER"] = [str(user_record_id)]

        new_record = stock_table.create(fields_data, typecast=True)
        print(f"✅ Successfully added new medication: {medicine_name}")
        return new_record
    except Exception as e:
        print(f"❌ Error adding new medication to cloud: {e}")
        return None


def update_medication_quantity(record_id, new_pill_count):
    """
    Updates the current pill count of an existing medication batch in the cloud.
    """
    try:
        fields_to_update = {
            "Current Pills Count": int(new_pill_count),
        }
        updated_record = stock_table.update(record_id, fields_to_update)
        print(f"✅ Successfully updated counts in cloud. Current Pills: {new_pill_count}")
        return updated_record
    except Exception as e:
        print(f"❌ Error updating medication quantity: {e}")
        return None


def update_medication_full_fields(record_id, medicine_name, barcode, active_ingredient, dosage, expiry_date,
                                  pills_count, batch_number, new_initial_count=None):
    """
    Updates fields of an existing medication record in the Available_Stock table.
    """
    try:
        fields_to_update = {
            "Medicine Name": str(medicine_name),
            "Barcode": str(barcode),
            "Active Ingredient": str(active_ingredient),
            "Dosage": str(dosage),
            "Expiry Date": str(expiry_date),
            "Current Pills Count": int(pills_count),
            "A Batch": str(batch_number)
        }

        if new_initial_count is not None:
            fields_to_update["Initial Pills Count"] = int(new_initial_count)

        updated_record = stock_table.update(record_id, fields_to_update, typecast=True)
        print(f"✅ Successfully updated medication record ID: {record_id}")
        return updated_record
    except Exception as e:
        print(f"❌ Error updating medication in cloud: {e}")
        return None


def delete_medication_record(record_id):
    """
    حذف سجل دواء/دفعة معينة بالكامل من قاعدة البيانات.
    """
    try:
        stock_table.delete(record_id)
        print(f"🗑️ Successfully purged medication record ID: {record_id}")
        return True
    except Exception as e:
        print(f"❌ Error deleting medication from cloud: {e}")
        return False


# =====================================================================
# 👥 SYSTEM USERS TABLE FUNCTIONS
# =====================================================================

def get_all_users():
    """
    Fetches all user records from the system users table in Airtable.
    """
    try:
        records = users_table.all()
        user_list = []
        for record in records:
            fields = record.fields.copy() if hasattr(record, 'fields') else record.get('fields', {}).copy()
            rec_id = record.id if hasattr(record, 'id') else record.get('id')

            # حماية حقول اليوزر عند السحب والعرض
            user_data = {
                "record_id": rec_id,
                "Username": safe_extract(fields.get("Username"), str),
                "Password": safe_extract(fields.get("Password"), str),
                "Role": safe_extract(fields.get("Role"), str),
                "PIN Code": safe_extract(fields.get("PIN Code"), str),
                "Full Name": safe_extract(fields.get("Full Name"), str),
                "Email": safe_extract(fields.get("Email"), str)
            }
            user_list.append(user_data)
        return user_list
    except Exception as e:
        print(f"❌ Error fetching users safely from Airtable: {e}")
        return []


def add_new_user(username, password, role, pin_code, full_name, email=""):
    """
    Creates a new user record in the SYSTEM_USERS table.
    """
    try:
        clean_role = str(role).strip()
        fields_data = {
            "Username": str(username).strip(),
            "Password": str(password).strip(),
            "Role": clean_role,
            "PIN Code": str(pin_code).strip(),
            "Full Name": str(full_name).strip(),
            "Email": str(email).strip(),
            "Last Login": ""
        }
        new_record = users_table.create(fields_data, typecast=True)
        return new_record
    except Exception as e:
        print(f"❌ Error adding new user to cloud: {e}")
        return None


def update_user_records(record_id, username, password, role, pin_code, full_name):
    """
    Updates an existing user record in the Users table.
    """
    try:
        fields_to_update = {
            "Username": str(username).strip(),
            "Password": str(password).strip(),
            "Role": str(role).strip(),
            "PIN Code": str(pin_code).strip(),
            "Full Name": str(full_name).strip()
        }
        updated_record = users_table.update(record_id, fields_to_update, typecast=True)
        return updated_record
    except Exception as e:
        print(f"❌ Error updating user in cloud: {e}")
        return None


def delete_user_record(record_id):
    """
    Deletes a user record permanently.
    """
    try:
        users_table.delete(record_id)
        return True
    except Exception as e:
        print(f"❌ Error deleting user from cloud: {e}")
        return False


def authenticate_user(username, password):
    """
    Verifies credentials against the cloud table using safe extractor.
    """
    try:
        formula = f"{{Username}} = '{username}'"
        records = users_table.all(formula=formula)
        if records:
            fields = records[0]['fields'] if hasattr(records[0], 'fields') else records[0].get('fields', {})
            db_password = safe_extract(fields.get("Password"), str)
            if db_password == str(password).strip():
                return safe_extract(fields.get("Role"), str)
        return None
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return None


# =====================================================================
# 📝 DISPENSED HISTORY TABLE FUNCTIONS
# =====================================================================

def log_transaction(action_type, barcode, action_by_user, quantity_taken, removal_reason=""):
    """
    Logs a new transaction to the Dispensed_History table.
    """
    try:
        fields_data = {
            "Action Type": str(action_type),
            "Barcode": str(barcode),
            "Action By User": str(action_by_user),
            "Quantity": int(quantity_taken)
        }

        if removal_reason:
            fields_data["Removal Reason"] = [str(removal_reason)]

        new_record = history_table.create(fields_data, typecast=True)
        return new_record
    except Exception as e:
        print(f"❌ Error logging transaction to cloud: {e}")
        return None


def get_all_history():
    """
    Fetches the entire transaction history from the cloud.
    """
    try:
        records = history_table.all()
        return records
    except Exception as e:
        print(f"❌ Error fetching transaction history: {e}")
        return []
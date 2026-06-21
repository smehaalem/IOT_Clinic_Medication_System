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
    Returns a list of raw records.
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
    Returns all active batches for a specific barcode.
    Uses 'Barcode lookup' field instead of linked Barcode field.
    """
    try:
        records = stock_table.all()

        batches = []

        for r in records:
            if hasattr(r, 'fields'):
                fields = r.fields
                rec_id = r.id
            else:
                fields = r.get('fields', {})
                rec_id = r.get('id')

            lookup_value = fields.get("Barcode lookup", [])

            # Airtable Lookup fields usually return a list
            if isinstance(lookup_value, list):
                lookup_value = str(lookup_value[0]) if lookup_value else ""

            if str(lookup_value).strip() != str(barcode).strip():
                continue

            qty = int(fields.get("Current Pills Count", 0))

            if qty <= 0:
                continue

            batches.append({
                "id": rec_id,
                "medicine_name": fields.get("Medicine Name", "Unknown"),
                "expiry_date": fields.get("Expiry Date", "9999-12-31"),
                "current_quantity": qty,
                "batch_number": fields.get("A Batch", "N/A")
            })

        batches.sort(key=lambda x: x["expiry_date"])
        return batches

    except Exception as e:
        print(f"❌ Error fetching all batches: {e}")
        return []


def add_new_medication(medicine_name, barcode, active_ingredient, dosage, expiry_date,
                       initial_pills, current_pills, batch_number, user_record_id=None):
    """
    Creates a new medication record in the Available_Stock table.
    Now links the logged-in user who inserted the batch.
    """
    try:
        fields_data = {
            "Medicine Name": str(medicine_name),
            "Barcode": str(barcode),
            "Active Ingredient": str(active_ingredient),
            "Dosage": str(dosage),
            "Expiry Date": str(expiry_date),  # Format: "YYYY-MM-DD"
            "Initial Pills Count": int(initial_pills),
            "Current Pills Count": int(current_pills),
            "A Batch": str(batch_number)
        }

        # 🔥 إذا تم تمرير الـ record_id للمستخدم، نقوم بربطه كقائمة داخل الحقل المخصص
        if user_record_id:
            fields_data["USER"] = [str(user_record_id)]

        new_record = stock_table.create(fields_data, typecast=True)  # تم إضافة typecast لضمان قبول الربط بسلاسة
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
                                  pills_count, batch_number):
    """
    Updates all fields of an existing medication record in the Available_Stock table (Correcting mistakes).
    """
    try:
        fields_to_update = {
            "Medicine Name": str(medicine_name),
            "Barcode": str(barcode),
            "Active Ingredient": str(active_ingredient),
            "Dosage": str(dosage),
            "Expiry Date": str(expiry_date),  # Format: "YYYY-MM-DD"
            "Current Pills Count": int(pills_count),
            "A Batch": str(batch_number)
        }
        updated_record = stock_table.update(record_id, fields_to_update, typecast=True)
        print(f"✅ Successfully updated medication record ID: {record_id}")
        return updated_record
    except Exception as e:
        print(f"❌ Error updating medication in cloud: {e}")
        return None


def delete_medication_record(record_id):
    """
    🔥 دالة خاصة بالـ Manager لحذف سجل دواء/دفعة معينة بالكامل من قاعدة البيانات.
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
            if hasattr(record, 'fields'):
                fields = record.fields.copy()
                fields['record_id'] = record.id
            else:
                fields = record.get('fields', {}).copy()
                fields['record_id'] = record.get('id')

            user_list.append(fields)
        return user_list
    except Exception as e:
        print(f"❌ Error fetching users from Airtable: {e}")
        return []


def add_new_user(username, password, role, pin_code, full_name):
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
            "Last Login": ""
        }
        print(f"🚀 Sending payload to Airtable: {fields_data}")
        new_record = users_table.create(fields_data, typecast=True)
        print(f"✅ Successfully added new user: {username} with role {clean_role}")
        return new_record
    except Exception as e:
        print(f"❌ Error adding new user to cloud: {e}")
        return None


def update_user_records(record_id, username, password, role, pin_code, full_name):
    """
    Updates an existing user record in the Users table by its Airtable record_id.
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
        print(f"✅ Successfully updated user record ID: {record_id}")
        return updated_record
    except Exception as e:
        print(f"❌ Error updating user in cloud: {e}")
        return None


def delete_user_record(record_id):
    """
    Deletes a user record from the Users table permanently by its Airtable record_id.
    """
    try:
        users_table.delete(record_id)
        print(f"🗑️ Successfully deleted user record ID: {record_id}")
        return True
    except Exception as e:
        print(f"❌ Error deleting user from cloud: {e}")
        return False


def authenticate_user(username, password):
    """
    Verifies credentials against the cloud table.
    """
    try:
        formula = f"{{Username}} = '{username}'"
        records = users_table.all(formula=formula)
        if records:
            user_fields = records[0]['fields'] if hasattr(records[0], 'fields') else records[0].get('fields', {})
            if user_fields.get("Password") == password:
                return user_fields.get("Role")
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
        print(f"✅ Successfully logged transaction: {action_type} for barcode {barcode}")
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
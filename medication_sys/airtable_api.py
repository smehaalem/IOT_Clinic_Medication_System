from pyairtable import Api
import config

# Initialize connection to the Airtable API cloud
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
        # Fixed field name to match your specific column 'Barcode'
        formula = f"{{Barcode}} = '{barcode_value}'"
        records = stock_table.all(formula=formula)
        if records:
            return records[0]
        return None
    except Exception as e:
        print(f"❌ Error searching medication by barcode: {e}")
        return None


def add_new_medication(medicine_name, barcode, active_ingredient, dosage, expiry_date,
                       initial_pills, current_pills, batch_number):
    """
    Creates a new medication record in the Available_Stock table.
    The dictionary keys strictly match your exact column names with spaces.
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
        new_record = stock_table.create(fields_data)
        print(f"✅ Successfully added new medication: {medicine_name}")
        return new_record
    except Exception as e:
        print(f"❌ Error adding new medication to cloud: {e}")
        return None


def update_medication_quantity(record_id, new_pill_count):
    """
    Updates the current pill count and remaining percentage of an existing medication in the cloud.
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

def get_all_users():
        """
        Fetches all user records from the system users table in Airtable.
        Returns a list of field dictionaries including their Airtable record ID.
        """
        try:
            records = users_table.all()
            user_list = []
            for record in records:
                fields = record['fields']
                fields['record_id'] = record['id']  # Save the internal ID if needed
                user_list.append(fields)
            return user_list
        except Exception as e:
            print(f"❌ Error fetching users: {e}")
            return []

def add_new_user(username, password, role):
        """
        Creates a new user record in the SYSTEM_USERS table.
        """
        try:
            fields_data = {
                "Username": str(username),
                "Password": str(password),
                "Role": str(role)  # e.g., "Clinic administrator", "Inventory Staff", "Doctor"
            }
            new_record = users_table.create(fields_data)
            print(f"✅ Successfully added new user: {username} with role {role}")
            return new_record
        except Exception as e:
            print(f"❌ Error adding new user to cloud: {e}")
            return None

def authenticate_user(username, password):
        """
        Verifies credentials against the cloud table.
        Returns the user's role string if successful, otherwise None.
        """
        try:
            formula = f"{{Username}} = '{username}'"
            records = users_table.all(formula=formula)
            if records:
                user_fields = records[0]['fields']
                if user_fields.get("Password") == password:
                    return user_fields.get("Role")
            return None
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            return None
# =================================================================
# Smart Clinic Kiosk - Medication Dispensing & Restocking Service
# =================================================================
import airtable_api
from datetime import datetime


def restock_medication(barcode, medicine_name, active_ingredient, dosage, expiry_date, pills_to_add, batch_number,
                       staff_name):
    """
    Handles inbound medication logic. Always creates a NEW RECORD for different batches/expiry dates.
    If the barcode already exists, it retrieves existing details from Airtable to ensure data consistency
    and avoid redundant manual user input.
    """
    print(f"\n[RESTOCK] Processing barcode: {barcode}")

    # Check if this barcode already exists anywhere in the database
    # We just need the first record to copy the static details (name, ingredient, dosage)
    existing_med_records = airtable_api.get_all_medications_by_barcode(barcode)

    if existing_med_records:
        existing_med = existing_med_records[0]  # Take the first one found
        fields = existing_med.get('fields', {})
        # Barcode found! Reuse official medication details from the cloud
        final_name = fields.get('Medicine Name', medicine_name)
        final_active = fields.get('Active Ingredient', active_ingredient)
        final_dosage = fields.get('Dosage', dosage)
        print(f"[RESTOCK] Existing barcode detected. Automatically retrieved details for: '{final_name}'")
    else:
        # Brand new barcode - use the manual information provided from the input
        print(f"[RESTOCK] New barcode detected. Using provided details for: '{medicine_name}'")
        final_name = medicine_name
        final_active = active_ingredient
        final_dosage = dosage

    # Strict Requirement: Always create a completely new record for independent batch/expiry tracking
    initial_pills = int(pills_to_add)
    current_pills = int(pills_to_add)

    new_record = airtable_api.add_new_medication(
        medicine_name=final_name,
        barcode=barcode,
        active_ingredient=final_active,
        dosage=final_dosage,
        expiry_date=expiry_date,
        initial_pills=initial_pills,
        current_pills=current_pills,
        batch_number=batch_number
    )

    # Log the transaction to the history table if stock was added successfully
    if new_record:
        airtable_api.log_transaction(
            action_type="Restock",
            barcode=barcode,
            action_by_user=staff_name,
            quantity_taken=pills_to_add,
            removal_reason=""
        )

    return new_record


def get_aggregated_stock_for_barcode(barcode):
    """
    Fetches all records for a given barcode and aggregates the current pill count
    based on the Expiry Date.
    Returns a dictionary grouped by expiry date.
    """
    records = airtable_api.get_all_medications_by_barcode(barcode)

    if not records:
        return {}  # No stock found

    aggregated_stock = {}

    for record in records:
        fields = record.get('fields', {})
        expiry_date = fields.get('Expiry Date', 'Unknown')
        current_pills = int(fields.get('Current Pills Count', 0))
        record_id = record['id']

        # We only want to show batches that actually have pills left
        if current_pills > 0:
            if expiry_date in aggregated_stock:
                aggregated_stock[expiry_date]['total_pills'] += current_pills
                # Keep track of all record IDs that make up this batch
                aggregated_stock[expiry_date]['record_ids'].append({'id': record_id, 'pills': current_pills})
            else:
                aggregated_stock[expiry_date] = {
                    'total_pills': current_pills,
                    'medicine_name': fields.get('Medicine Name', 'Unknown'),
                    'record_ids': [{'id': record_id, 'pills': current_pills}]
                }

    return aggregated_stock


def dispense_medication_to_patient(barcode, record_id, pills_to_dispense, doctor_name):
    """
    Handles outbound medication logic (Dispensing pills to a specific patient).
    Now takes a specific record_id to deduct from the exact batch chosen by the user.
    """
    print(f"\n[DISPENSE] Request to dispense {pills_to_dispense} pills from record ID: {record_id}")

    # We need to fetch the specific record to know its current state
    try:
        med_record = airtable_api.stock_table.get(record_id)
    except Exception as e:
        print(f"❌ Dispense Failed: Could not find specific record. Error: {e}")
        return {"success": False, "message": "Specific batch not found in stock."}

    fields = med_record.get('fields', {})
    medicine_name = fields.get("Medicine Name", "Unknown")
    current_pills = int(fields.get("Current Pills Count", 0))
    initial_pills = int(fields.get("Initial Pills Count", 1))

    if current_pills < int(pills_to_dispense):
        print(
            f"❌ Dispense Failed: Insufficient stock in this batch. Available: {current_pills}, Requested: {pills_to_dispense}")
        return {"success": False, "message": f"Insufficient stock in selected batch. Only {current_pills} left."}

    updated_current = current_pills - int(pills_to_dispense)
    new_quantity_remaining = (updated_current / initial_pills) * 100.0

    airtable_api.update_medication_quantity(record_id, updated_current)
    print(f"✅ Dispense Successful: {pills_to_dispense} pills of {medicine_name} deducted from batch.")

    airtable_api.log_transaction(
        action_type="Dispense",
        barcode=barcode,
        action_by_user=doctor_name,
        quantity_taken=pills_to_dispense,
        removal_reason="Dispensed to Patient"
    )

    return {
        "success": True,
        "medicine_name": medicine_name,
        "pills_left": updated_current,
        "percentage_left": new_quantity_remaining
    }
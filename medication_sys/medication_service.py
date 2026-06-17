# =================================================================
# Smart Clinic Kiosk - Medication Dispensing & Restocking Service
# =================================================================
import airtable_api


def restock_medication(barcode, medicine_name, active_ingredient, dosage, expiry_date, pills_to_add, batch_number):
    """
    Handles inbound medication logic. Always creates a NEW RECORD for different batches/expiry dates.
    If the barcode already exists, it retrieves existing details from Airtable to ensure data consistency
    and avoid redundant manual user input.
    """
    print(f"\n[RESTOCK] Processing barcode: {barcode}")

    # Check if this barcode already exists anywhere in the database
    existing_med = airtable_api.find_medication_by_barcode(barcode)

    if existing_med:
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

    return airtable_api.add_new_medication(
        medicine_name=final_name,
        barcode=barcode,
        active_ingredient=final_active,
        dosage=final_dosage,
        expiry_date=expiry_date,
        initial_pills=initial_pills,
        current_pills=current_pills,
        batch_number=batch_number
    )


def dispense_medication_to_patient(barcode, patient_id, pills_to_dispense, doctor_name):
    """
    Handles outbound medication logic (Dispensing pills to a specific patient).
    """
    print(f"\n[DISPENSE] Request to dispense {pills_to_dispense} pills from barcode: {barcode}")

    med_record = airtable_api.find_medication_by_barcode(barcode)

    if not med_record:
        print("❌ Dispense Failed: Barcode not found in system stock.")
        return {"success": False, "message": "Barcode not found in stock."}

    record_id = med_record['id']
    fields = med_record.get('fields', {})
    medicine_name = fields.get("Medicine Name", "Unknown")
    current_pills = int(fields.get("Current Pills Count", 0))
    initial_pills = int(fields.get("Initial Pills Count", 1))

    if current_pills < int(pills_to_dispense):
        print(f"❌ Dispense Failed: Insufficient stock. Available: {current_pills}, Requested: {pills_to_dispense}")
        return {"success": False, "message": f"Insufficient stock. Only {current_pills} left."}

    updated_current = current_pills - int(pills_to_dispense)
    new_quantity_remaining = (updated_current / initial_pills) * 100.0

    airtable_api.update_medication_quantity(record_id, updated_current)
    print(f"✅ Dispense Successful: {pills_to_dispense} pills of {medicine_name} allocated to Patient {patient_id}")

    return {
        "success": True,
        "medicine_name": medicine_name,
        "pills_left": updated_current,
        "percentage_left": new_quantity_remaining
    }
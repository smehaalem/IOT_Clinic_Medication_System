import medication_service
import time

print("\n--- Starting Clean Live Service Test ---")

# Let's use a unique barcode for our official live test
test_barcode = "999888777"  # 🔹 Testing on a fresh barcode to ensure clean stock

# 1. Test Inbound Restock (Adding Optalgin Pack)
print("\n--- Testing Inbound Restock ---")
medication_service.restock_medication(
    barcode=test_barcode,
    medicine_name="Optalgin Drops",
    active_ingredient="Dipyrone",
    dosage="500mg/ml",
    expiry_date="2028-09-15",
    pills_to_add=65,
    batch_number="OPT-XYZ-2026",
    staff_name="Nurse Rachel"
)

time.sleep(2)  # Delay for cloud database replication sync

# 2. Test Outbound Dispense
print("\n--- Testing Outbound Dispense (Workflow) ---")

# Step A: The GUI requests available stock for the scanned barcode
print("Fetching aggregated stock from cloud...")
available_stock = medication_service.get_aggregated_stock_for_barcode(test_barcode)

if available_stock:
    # Let's pretend the user clicked on the first Expiry Date group they saw on screen
    first_expiry_date = list(available_stock.keys())[0]
    batch_data = available_stock[first_expiry_date]

    # We get the specific internal 'record_id' of the first pack in that group
    specific_record_id_to_use = batch_data['record_ids'][0]['id']
    print(f"User selected batch expiring on {first_expiry_date}. Internal Record ID: {specific_record_id_to_use}")

    # Step B: Now we do the actual dispensing using that specific record_id
    result = medication_service.dispense_medication_to_patient(
        barcode=test_barcode,
        record_id=specific_record_id_to_use,  # 🔹 We pass the specific record ID here!
        pills_to_dispense=10,
        doctor_name="Dr. Levi"
    )

    if result["success"]:
        print(f"\n🎉 Test Passed Completely! Cloud Stock updated successfully.")
else:
    print("❌ Cannot dispense: No stock found for this barcode.")
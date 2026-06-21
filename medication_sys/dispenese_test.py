import medication_service
from datetime import datetime

print("\n=======================================================")
print("  🧪 TEST: OUTBOUND DISPENSE (Removing Medication) 🧪")
print("=======================================================\n")

# --- VARIABLES TO PLAY WITH ---
# Change these values to test different scenarios
TEST_BARCODE = "888113434342"
PILLS_TO_DISPENSE = 12
DOCTOR_NAME = "Dr. Levi"

print(f"🔍 Step 1: Searching for available stock for barcode '{TEST_BARCODE}'...")

# 1. Fetch available stock
available_stock = medication_service.get_aggregated_stock_for_barcode(TEST_BARCODE)

if not available_stock:
    print(f"❌ TEST FAILED: No stock found for barcode {TEST_BARCODE}. Please run the restock test first!")
else:
    print(f"✅ Stock found! Grouped by Expiry Date:")

    # Just printing the options to the console so you can see what the GUI will see
    for expiry, data in available_stock.items():
        print(f"  - Expiry: {expiry} | Total Pills: {data['total_pills']} | Batches: {len(data['record_ids'])}")

    # 2. Simulate User Selection: Find the earliest expiry date with enough pills
    selected_expiry = None
    target_record_id = None

    # Sort the expiry dates to find the earliest one first (FEFO - First Expire First Out)
    # Filter out 'Unknown' or invalid dates first if needed, but assuming valid "YYYY-MM-DD"
    sorted_expiries = sorted([date for date in available_stock.keys() if date != 'Unknown'])

    # If 'Unknown' was the only key, handle it, otherwise append it to end
    if 'Unknown' in available_stock:
        sorted_expiries.append('Unknown')

    for expiry in sorted_expiries:
        batch_data = available_stock[expiry]

        # We need to find a specific record within this expiry group that has enough pills
        for record in batch_data['record_ids']:
            if record['pills'] >= PILLS_TO_DISPENSE:
                selected_expiry = expiry
                target_record_id = record['id']
                break  # Found a suitable record in this expiry group

        if selected_expiry:
            break  # Stop checking other expiry dates once we found one

    if target_record_id:
        print(f"\n👆 Simulating GUI selection (FEFO logic)... User selected Expiry: {selected_expiry}")
        print(f"🔄 Attempting to dispense {PILLS_TO_DISPENSE} pills from Record ID: {target_record_id}...")

        # 3. Perform the dispense action
        try:
            result = medication_service.dispense_medication_to_patient(
                barcode=TEST_BARCODE,
                record_id=target_record_id,
                pills_to_dispense=PILLS_TO_DISPENSE,
                doctor_name=DOCTOR_NAME
            )

            if result.get("success"):
                print("\n✅ DISPENSE TEST SUCCESSFUL!")
                print(f"Medicine: {result.get('medicine_name')}")
                print(f"Pills Left in this batch: {result.get('pills_left')}")
            else:
                print(f"\n❌ DISPENSE TEST FAILED: {result.get('message')}")

        except Exception as e:
            print(f"\n💥 UNEXPECTED ERROR DURING DISPENSE: {e}")
    else:
        print(
            f"\n❌ DISPENSE TEST FAILED: No single batch has enough pills ({PILLS_TO_DISPENSE}) to fulfill the request.")
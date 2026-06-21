import medication_service

print("\n=======================================================")
print("  🧪 TEST: INBOUND RESTOCK (Adding Medication) 🧪")
print("=======================================================\n")

# --- VARIABLES TO PLAY WITH ---
# Change these values to test different scenarios
TEST_BARCODE = "888113434342"
MEDICINE_NAME = "Acamol Focus"
ACTIVE_INGREDIENT = "Paracetamol 500mg"
DOSAGE = "1-2 pills every 6 hours"
EXPIRY_DATE = "2027-12-31"  # Format: YYYY-MM-DD
PILLS_TO_ADD = 100
BATCH_NUMBER = "BCH-2024-AC"
STAFF_NAME = "Nurse Rachel"  # Note: Must match a user if your Airtable field requires it

print(f"🔄 Attempting to restock {PILLS_TO_ADD} pills of {MEDICINE_NAME}...")

try:
    result = medication_service.restock_medication(
        barcode=TEST_BARCODE,
        medicine_name=MEDICINE_NAME,
        active_ingredient=ACTIVE_INGREDIENT,
        dosage=DOSAGE,
        expiry_date=EXPIRY_DATE,
        pills_to_add=PILLS_TO_ADD,
        batch_number=BATCH_NUMBER,
        staff_name=STAFF_NAME
    )

    if result:
        print("\n✅ RESTOCK TEST SUCCESSFUL!")
        print(f"Record created in Airtable with ID: {result.get('id')}")
    else:
        print("\n❌ RESTOCK TEST FAILED. Check console for specific API errors.")

except Exception as e:
    print(f"\n💥 UNEXPECTED ERROR DURING RESTOCK: {e}")
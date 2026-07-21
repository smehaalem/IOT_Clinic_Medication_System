# MedGate

Smart patient and medication management system for a community clinic.

MedGate is a Raspberry Pi–based kiosk application developed in collaboration with the Technion Social Hub. It combines patient registration and check-in, medication inventory management, dispensing, staff access control, low-stock reporting, and patient-card printing in one touchscreen interface.

## Project Contributors

- Samiha Alem
- Raghad Khalil
- Rabab Jamal

## Main Capabilities

### Patient Management

- Register new patients in Airtable.
- Generate a patient identification card containing the patient's name, ID, and a QR code.
- Check in returning patients using an exact Personal ID or exact full-name search.
- Edit or delete an existing patient record.
- Save changes and print a replacement card.

### Medication Management

- Add new medicines and independent stock batches.
- Search existing medicines by barcode or medicine name.
- Reuse existing medicine details when adding another batch.
- Edit an existing batch.
- View active stock grouped by medicine name.
- Hide zero-quantity stock from active-stock views.
- Search stock by medicine name, category, barcode, or active ingredient.
- Dispense medicine by barcode or medicine name.
- Include all available batches belonging to the same medicine.
- Use earliest-expiry-first allocation unless staff explicitly select batches.
- Record dispensing history, staff identity, quantity, and doctor name.
- Display low-stock medicines using the catalog threshold.

### Administration and Kiosk Operation

- Authenticate staff before entering medication operations.
- Cache staff accounts for offline login.
- Manage staff accounts from the manager portal.
- Permanently discard stock batches from the manager portal.
- Run in full-screen kiosk mode.
- Protect application exit with a developer password.
- Use frameless confirmation and validation dialogs suitable for the Raspberry Pi kiosk.

## Hardware

The application is designed for the following setup:

- Raspberry Pi 4
- 7-inch touchscreen in landscape orientation
- USB barcode scanner operating as a keyboard
- Brother QL-700 label printer
- CUPS print service with a queue named `brotherql700`

The interface is optimized around an 800×480 display.

## Repository Structure

```text
.
├── Clinic/
│   ├── kiosk_main.py
│   ├── checkingui.py
│   ├── add_patient_screen.py
│   ├── edit_patient_screen.py
│   ├── printer_engine.py
│   └── README.md
├── medication_sys/
│   ├── medicine_menu.py
│   ├── airtable_api.py
│   ├── local_db.py
│   ├── inventory_check.py
│   ├── medication_service.py
│   ├── screen/
│   │   ├── __init__.py
│   │   ├── login_dialog.py
│   │   ├── stock_page.py
│   │   ├── dispense_page.py
│   │   ├── inventory_view_page.py
│   │   ├── admin_page.py
│   │   └── README.md
│   ├── tests/
│   └── README.md
├── Unit Tests/
│   └── README.md
├── docs/
│   └── README.md
└── README.md
```

## Software Requirements

### Python packages

```bash
python3 -m pip install PyQt5 pyairtable python-dotenv qrcode Pillow requests
```

`requests` is only required by the Airtable metadata test.

### System requirements

- Python 3
- Linux or Raspberry Pi OS
- CUPS
- A configured Brother printer driver and queue
- The commands `lp`, `lpstat`, and `lsusb`
- Tkinter support for the Python installation

## Configuration

Create this file:

```text
medication_sys/.env
```

Add:

```env
AIRTABLE_TOKEN=your_airtable_personal_access_token
BASE_ID=your_airtable_base_id
KIOSK_EXIT_PASSWORD=your_kiosk_exit_password
```

Do not commit the real `.env` file.

The application uses these Airtable tables:

- `Available Stock`
- `History`
- `Users`
- `Patients`
- `Medicines Catalog`
- `Mock` for legacy/mock workflows

See [`docs/README.md`](docs/README.md) for the expected fields and data flow.

## Running the Complete Application

From the repository root:

```bash
cd medication_sys
python3 medicine_menu.py
```

The main application opens in full-screen kiosk mode and provides access to both medication operations and the patient kiosk.

## Running the Patient Kiosk Separately

```bash
cd Clinic
python3 kiosk_main.py
```

## Offline Behavior

Medication operations use a local SQLite database:

```text
medication_sys/clinic_local.db
```

The local database stores:

- Medicine stock
- Cached users
- Local history
- Pending synchronization operations

Medicine stock changes are written locally and queued when Airtable is unavailable. Cached users allow staff login without internet after at least one successful online cache refresh.

Patient registration, patient editing, patient check-in, staff administration, and the low-stock catalog still depend on Airtable connectivity.

## Tests

Hardware validation scripts are under:

```text
Unit Tests/
```

Developer and integration scripts are under:

```text
medication_sys/tests/
```

Read the README inside each test directory before running a script. Some developer scripts can read from or modify the connected Airtable base.

## Generated Local Files

The application may generate the following files during operation:

```text
medication_sys/clinic_local.db
Clinic/last_patient_label.png
Clinic/last_edited_patient_label.png
```

These files should normally remain outside Git.

## Additional Documentation

- [`Clinic/README.md`](Clinic/README.md)
- [`medication_sys/README.md`](medication_sys/README.md)
- [`medication_sys/screen/README.md`](medication_sys/screen/README.md)
- [`Unit Tests/README.md`](Unit%20Tests/README.md)
- [`docs/README.md`](docs/README.md)

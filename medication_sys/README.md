# Medication Management Module

This directory contains the staff-facing medication system, offline data layer, Airtable integration, and main kiosk application.

## Entry Point

```bash
cd medication_sys
python3 medicine_menu.py
```

The application launches in full-screen kiosk mode.

## Main Files

### `medicine_menu.py`

Main application router.

- Opens the medication login flow.
- Opens the patient kiosk.
- Maintains the authenticated staff session.
- Displays medication operations according to the logged-in role.
- Protects application exit with `KIOSK_EXIT_PASSWORD`.
- Warms the offline cache during startup.

### `airtable_api.py`

Shared data-access layer.

- Wraps the Airtable stock and history tables.
- Writes medicine changes to SQLite first.
- Falls back to local records while offline.
- Queues pending create, update, delete, and history operations.
- Caches staff accounts for offline login.
- Synchronizes medicine identity data into `Medicines Catalog`.

### `local_db.py`

SQLite persistence layer.

The database file is:

```text
clinic_local.db
```

It contains:

- `medicines`
- `users_cache`
- `local_history`
- `sync_queue`

### `inventory_check.py`

Creates the embedded low-stock report from `Medicines Catalog`.

A medicine is included when:

```text
Total Valid Quantity < Minimum Required
```

The visible report contains medicine name, category/use, and available quantity.

### `medication_service.py`

Older service-level restock and dispense helpers.

The current graphical workflow mainly operates through the screen classes and `airtable_api.py`. Treat this file as a legacy/developer helper unless it is intentionally connected to a new workflow.

### `screen/`

Contains the login, stock, dispensing, active-stock, and administration screens. See [`screen/README.md`](screen/README.md).

### `tests/`

Contains developer and integration scripts. See [`tests/README.md`](tests/README.md).

## Medication Workflows

### Add or Update Stock

Staff can search by barcode or medicine name.

- Existing batches are displayed before creating another batch.
- Name search includes every stock row with the exact same medicine name, including rows originally created through barcode search.
- Barcode search includes every matching barcode record.
- The user can edit a selected batch or create a new batch.
- Expiry is selected as month and year; the stored Airtable date uses the last day of that month.

### Active Stock

- Groups batches by medicine name.
- Shows the total available quantity.
- Hides batches whose quantity is zero or lower.
- Supports search by medicine name, category/use, barcode, and active ingredient.
- Opens a batch-level breakdown.

### Dispensing

- Supports selection by barcode or medicine name.
- Loads all available batches belonging to the selected medicine.
- Uses earliest expiry first unless staff select specific batches.
- Requests the doctor name before completion.
- Shows a single final confirmation.
- Updates quantity by record ID.
- Writes a history record with the logged-in staff member.

### Low Stock

Reads the cloud `Medicines Catalog` table and displays medicines below their configured threshold.

### Administration

The manager portal supports:

- Staff-account creation and editing
- Staff-account deletion
- Disposal inventory
- Permanent batch deletion with confirmation
- Disposal history logging

## Offline-First Scope

Supported locally:

- Medicine-stock reads
- Medicine additions
- Medicine quantity updates
- Medicine field updates
- Medicine deletions
- Dispensing history queue
- Cached staff login

Cloud-dependent features:

- Patient workflows
- Staff-account administration
- Low-stock catalog report
- Catalog synchronization while no internet is available

## Configuration

Create:

```text
.env
```

inside `medication_sys/`:

```env
AIRTABLE_TOKEN=your_airtable_personal_access_token
BASE_ID=your_airtable_base_id
KIOSK_EXIT_PASSWORD=your_kiosk_exit_password
```

Configured Airtable table names are defined in `config.py`.

## Required Module

`airtable_api.py` imports `sync_manager`.

The reviewed archive does not contain:

```text
medication_sys/sync_manager.py
```

This file must provide the internet check and pending-operation synchronization used by the hybrid data layer.

## Dependencies

```bash
python3 -m pip install PyQt5 pyairtable python-dotenv
```

The complete repository also uses `qrcode`, `Pillow`, and `requests` in other modules and tests.

## Generated File

```text
clinic_local.db
```

The database is created automatically and should normally not be committed.

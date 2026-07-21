# Medication UI Screens

This directory contains the staff-facing screens used by `medicine_menu.py`.

These files are application pages, not standalone entry points.

## `login_dialog.py`

Staff authentication dialog.

- Loads users from Airtable when online.
- Falls back to the SQLite user cache when offline.
- Returns the authenticated Airtable record and role.
- Uses a kiosk-safe frameless dialog.

## `stock_page.py`

Add and update stock.

- Search by barcode or exact medicine name.
- Display all existing batches for the selected medicine.
- Include name-created and barcode-created batches under the same medicine name.
- Create a new batch or edit the selected batch.
- Preserve or resolve a real barcode when possible.
- Store expiry using the last day of the chosen month.
- Use custom frameless confirmation and validation dialogs.

## `dispense_page.py`

Medication dispensing.

- Search by barcode, medicine name, category, active ingredient, or batch.
- Display one summary row per medicine name.
- Load all positive-quantity batches under the selected medicine.
- Allocate by earliest expiry unless batches are selected manually.
- Require a doctor name.
- Show the final allocation before saving.
- Record the action under the logged-in staff member.
- Use custom frameless dialogs for messages, doctor input, and confirmation.

## `inventory_view_page.py`

Active-stock browser.

- Refreshes whenever the page is opened.
- Hides zero-quantity rows.
- Groups stock by medicine name.
- Shows total quantity and batch-level details.
- Filters by medicine name, category/use, barcode, or active ingredient.

## `admin_page.py`

Manager portal.

- Create and edit staff accounts.
- Delete staff accounts.
- Require an email for the manager role.
- Display positive-quantity disposal inventory.
- Permanently discard a selected medicine batch.
- Use custom frameless validation, status, and confirmation dialogs.

## Navigation

The screens receive callbacks from `MedicineSystemApp` rather than closing the whole application.

The authenticated session is passed to:

- `MedicationManagementPage`
- `DispenseMedicationPage`

This allows restock and dispensing records to identify the logged-in staff member.

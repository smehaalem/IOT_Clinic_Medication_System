# Medication Developer Tests

This directory contains developer scripts and prototypes. They are not a unified automated test suite.

Review each script before running it against a real Airtable base.

## `testlogin.py`

Standalone PyQt login and user-management prototype using an in-memory mock backend.

Run:

```bash
cd medication_sys
python3 tests/testlogin.py
```

It does not use the production login screen.

## `testtables.py`

Reads Airtable base metadata and prints the available tables.

Requirements:

- `AIRTABLE_TOKEN`
- `BASE_ID`
- `requests`
- Airtable token permission to read base schema metadata

Run:

```bash
cd medication_sys
python3 tests/testtables.py
```

This script performs a live API request but does not modify tables.

## `testservice.py`

Legacy live restock/dispense workflow test.

This script can create stock, dispense stock, and write history in the connected Airtable base. Its function calls are not fully aligned with the current `medication_service.py` signatures, so update and review it before use.

Do not run it against production clinic data without intentionally choosing test records.

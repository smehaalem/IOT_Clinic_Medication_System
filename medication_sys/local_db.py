"""
Local SQLite storage for Smart Clinic Kiosk medicine offline mode.

This module stores a local copy of the medicine stock and a queue of cloud
operations that still need to be synchronized with Airtable.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime

DB_FILENAME = "clinic_local.db"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        if isinstance(value, list):
            value = value[0] if value else default
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return default


def safe_str(value, default=""):
    if value is None:
        return default
    if isinstance(value, list):
        value = value[0] if value else default
    return str(value).strip()


def clean_barcode_value(value):
    """Return the real scanner barcode and ignore Airtable record IDs/placeholders."""
    if value is None:
        return ""

    values = value if isinstance(value, list) else [value]
    for current in values:
        if isinstance(current, dict):
            current = current.get("text") or current.get("value") or current.get("name") or ""
        text = str(current).strip()
        low = text.lower()

        if low in ("", "none", "null", "nan", "barcode", "no_barcode", "n/a"):
            continue
        if low.startswith("rec") and len(text) >= 10:
            continue
        return text

    return ""


def extract_real_barcode(fields):
    """Extract barcode from all field names used by this Airtable base."""
    fields = fields or {}
    candidates = [
        fields.get("Search key (auto 12)"),
        fields.get("Barcode (from Barcode)"),
        fields.get("Barcode lookup"),
        fields.get("Barcode"),
    ]
    for candidate in candidates:
        clean = clean_barcode_value(candidate)
        if clean:
            return clean
    return ""


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                record_id TEXT PRIMARY KEY,
                barcode TEXT,
                barcode_lookup TEXT,
                medicine_name TEXT,
                category TEXT,
                active_ingredient TEXT,
                dosage TEXT,
                expiry_date TEXT,
                current_pills_count INTEGER DEFAULT 0,
                initial_pills_count INTEGER DEFAULT 0,
                batch_number TEXT,
                fields_json TEXT NOT NULL,
                dirty INTEGER DEFAULT 0,
                deleted INTEGER DEFAULT 0,
                updated_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_medicines_barcode ON medicines(barcode)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_medicines_barcode_lookup ON medicines(barcode_lookup)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_medicines_name ON medicines(medicine_name)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users_cache (
                record_id TEXT PRIMARY KEY,
                fields_json TEXT NOT NULL,
                updated_at TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS local_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                barcode TEXT,
                action_by_user TEXT,
                quantity INTEGER,
                removal_reason TEXT,
                doctor TEXT,
                created_at TEXT,
                synced INTEGER DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                record_id TEXT,
                payload_json TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()


def _record_id_from(record):
    if hasattr(record, "id"):
        return record.id
    if isinstance(record, dict):
        return record.get("id") or record.get("record_id")
    return None


def _fields_from(record):
    if hasattr(record, "fields"):
        return dict(record.fields or {})
    if isinstance(record, dict):
        return dict(record.get("fields", record) or {})
    return {}


def make_record(record_id, fields):
    return {"id": str(record_id), "fields": dict(fields or {})}


def make_local_id():
    return "local_" + uuid.uuid4().hex[:18]


def is_local_id(record_id):
    return str(record_id).startswith("local_")


def _normalize_fields(fields):
    fields = dict(fields or {})

    # Store the real scanner barcode in both local barcode columns.
    # In Airtable the visible field can be named "Barcode (from Barcode)"
    # while the field "Barcode" may contain linked-record ids such as recXXXX.
    real_barcode = extract_real_barcode(fields)
    if real_barcode:
        fields["Barcode"] = real_barcode
        fields["Barcode lookup"] = real_barcode

    # Some project versions called the initial amount "Valid Pills Count".
    if "Initial Pills Count" not in fields and "Valid Pills Count" in fields:
        fields["Initial Pills Count"] = fields.get("Valid Pills Count")
    if "Valid Pills Count" not in fields and "Initial Pills Count" in fields:
        fields["Valid Pills Count"] = fields.get("Initial Pills Count")

    if "Category" not in fields and "A Category" in fields:
        fields["Category"] = fields.get("A Category")

    return fields


def upsert_medicine_record(record, dirty=0):
    init_db()
    record_id = _record_id_from(record) or make_local_id()
    fields = _normalize_fields(_fields_from(record))

    barcode = safe_str(fields.get("Barcode"))
    barcode_lookup = safe_str(fields.get("Barcode lookup") or barcode)
    medicine_name = safe_str(fields.get("Medicine Name"))
    category = safe_str(fields.get("Category") or fields.get("A Category"))
    active_ingredient = safe_str(fields.get("Active Ingredient"))
    dosage = safe_str(fields.get("Dosage") or fields.get("Strength"))
    expiry_date = safe_str(fields.get("Expiry Date"))
    current_qty = safe_int(fields.get("Current Pills Count") or fields.get("Quantity") or fields.get("Pills Count"), 0)
    initial_qty = safe_int(fields.get("Initial Pills Count") or fields.get("Valid Pills Count"), current_qty)
    batch = safe_str(fields.get("A Batch") or fields.get("Batch Number"))

    with _connect() as conn:
        conn.execute("""
            INSERT INTO medicines (
                record_id, barcode, barcode_lookup, medicine_name, category,
                active_ingredient, dosage, expiry_date, current_pills_count,
                initial_pills_count, batch_number, fields_json, dirty, deleted, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(record_id) DO UPDATE SET
                barcode=excluded.barcode,
                barcode_lookup=excluded.barcode_lookup,
                medicine_name=excluded.medicine_name,
                category=excluded.category,
                active_ingredient=excluded.active_ingredient,
                dosage=excluded.dosage,
                expiry_date=excluded.expiry_date,
                current_pills_count=excluded.current_pills_count,
                initial_pills_count=excluded.initial_pills_count,
                batch_number=excluded.batch_number,
                fields_json=excluded.fields_json,
                dirty=CASE WHEN medicines.dirty = 1 THEN 1 ELSE excluded.dirty END,
                deleted=0,
                updated_at=excluded.updated_at
        """, (
            str(record_id), barcode, barcode_lookup, medicine_name, category,
            active_ingredient, dosage, expiry_date, current_qty, initial_qty, batch,
            json.dumps(fields, ensure_ascii=False), int(dirty), now_iso()
        ))
        conn.commit()
    return make_record(record_id, fields)


def create_local_medicine(fields, record_id=None, dirty=1):
    record_id = record_id or make_local_id()
    return upsert_medicine_record(make_record(record_id, fields), dirty=dirty)


def _row_to_record(row):
    fields = json.loads(row["fields_json"] or "{}")
    fields = _normalize_fields(fields)
    return make_record(row["record_id"], fields)


def get_all_medicine_records(include_deleted=False):
    init_db()
    with _connect() as conn:
        if include_deleted:
            rows = conn.execute("SELECT * FROM medicines ORDER BY medicine_name, expiry_date").fetchall()
        else:
            rows = conn.execute("SELECT * FROM medicines WHERE deleted = 0 ORDER BY medicine_name, expiry_date").fetchall()
    return [_row_to_record(row) for row in rows]


def get_medicine_record(record_id):
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM medicines WHERE record_id = ? AND deleted = 0",
            (str(record_id),)
        ).fetchone()
    return _row_to_record(row) if row else None


def find_medicines_by_barcode(barcode):
    init_db()
    clean = safe_str(barcode)
    with _connect() as conn:
        rows = conn.execute("""
            SELECT * FROM medicines
            WHERE deleted = 0 AND (barcode = ? OR barcode_lookup = ?)
            ORDER BY expiry_date
        """, (clean, clean)).fetchall()
    return [_row_to_record(row) for row in rows]


def find_medicines_by_name_exact(name):
    init_db()
    clean = safe_str(name).lower()
    with _connect() as conn:
        rows = conn.execute("""
            SELECT * FROM medicines
            WHERE deleted = 0 AND LOWER(medicine_name) = ?
            ORDER BY expiry_date
        """, (clean,)).fetchall()
    return [_row_to_record(row) for row in rows]


def update_medicine_fields(record_id, fields_update, dirty=1):
    init_db()
    current = get_medicine_record(record_id)
    if current:
        fields = dict(current.get("fields", {}))
        fields.update(fields_update or {})
    else:
        fields = dict(fields_update or {})
    return upsert_medicine_record(make_record(record_id, fields), dirty=dirty)


def delete_medicine_record(record_id, dirty=1):
    init_db()
    with _connect() as conn:
        conn.execute(
            "UPDATE medicines SET deleted = 1, dirty = ?, updated_at = ? WHERE record_id = ?",
            (int(dirty), now_iso(), str(record_id))
        )
        conn.commit()


def replace_medicine_record_id(old_record_id, new_record):
    """Used after an offline-created medicine gets a real Airtable record id."""
    init_db()
    new_record_id = _record_id_from(new_record)
    if not new_record_id:
        return
    fields = _normalize_fields(_fields_from(new_record))

    with _connect() as conn:
        conn.execute("DELETE FROM medicines WHERE record_id = ?", (str(old_record_id),))
        conn.execute(
            "UPDATE sync_queue SET record_id = ? WHERE record_id = ?",
            (str(new_record_id), str(old_record_id))
        )
        conn.commit()
    upsert_medicine_record(make_record(new_record_id, fields), dirty=0)


def cache_users(user_list):
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM users_cache")
        for user in user_list:
            rec_id = str(user.get("record_id") or user.get("id") or make_local_id())
            conn.execute(
                "INSERT OR REPLACE INTO users_cache(record_id, fields_json, updated_at) VALUES (?, ?, ?)",
                (rec_id, json.dumps(user, ensure_ascii=False), now_iso())
            )
        conn.commit()


def get_cached_users():
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM users_cache ORDER BY record_id").fetchall()
    users = []
    for row in rows:
        data = json.loads(row["fields_json"] or "{}")
        data.setdefault("record_id", row["record_id"])
        users.append(data)
    return users


def add_local_history(action_type, barcode, action_by_user, quantity, removal_reason="", doctor="", synced=0):
    init_db()
    with _connect() as conn:
        cur = conn.execute("""
            INSERT INTO local_history(action_type, barcode, action_by_user, quantity,
                                      removal_reason, doctor, created_at, synced)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(action_type), str(barcode), str(action_by_user), int(quantity),
              str(removal_reason), str(doctor), now_iso(), int(synced)))
        conn.commit()
        return cur.lastrowid


def enqueue_operation(operation_type, record_id, payload):
    init_db()
    with _connect() as conn:
        cur = conn.execute("""
            INSERT INTO sync_queue(operation_type, record_id, payload_json, status,
                                   retry_count, last_error, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', 0, '', ?, ?)
        """, (
            str(operation_type),
            str(record_id) if record_id is not None else "",
            json.dumps(payload or {}, ensure_ascii=False),
            now_iso(), now_iso()
        ))
        conn.commit()
        return cur.lastrowid


def get_pending_operations(limit=100):
    init_db()
    with _connect() as conn:
        rows = conn.execute("""
            SELECT * FROM sync_queue
            WHERE status IN ('pending', 'failed')
            ORDER BY id ASC
            LIMIT ?
        """, (int(limit),)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.get("payload_json") or "{}")
        result.append(item)
    return result


def mark_operation_synced(operation_id):
    init_db()
    with _connect() as conn:
        conn.execute(
            "UPDATE sync_queue SET status = 'synced', updated_at = ?, last_error = '' WHERE id = ?",
            (now_iso(), int(operation_id))
        )
        conn.commit()


def mark_operation_failed(operation_id, error_message):
    init_db()
    with _connect() as conn:
        conn.execute("""
            UPDATE sync_queue
            SET status = 'failed', retry_count = retry_count + 1,
                last_error = ?, updated_at = ?
            WHERE id = ?
        """, (str(error_message)[:500], now_iso(), int(operation_id)))
        conn.commit()


def pending_count():
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM sync_queue WHERE status IN ('pending', 'failed')"
        ).fetchone()
    return int(row["c"] if row else 0)

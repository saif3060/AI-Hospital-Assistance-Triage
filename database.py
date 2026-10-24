"""SQLite persistence for the educational hospital triage prototype."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parents[1] / "hospital_triage.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_code TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK(age BETWEEN 0 AND 120),
    symptom_group TEXT NOT NULL,
    symptoms TEXT NOT NULL,
    symptom_duration TEXT NOT NULL,
    observations TEXT NOT NULL DEFAULT '',
    possible_emergency_warning_sign INTEGER NOT NULL DEFAULT 0,
    required_information_complete INTEGER NOT NULL DEFAULT 1,
    human_review_requested INTEGER NOT NULL DEFAULT 0,
    priority TEXT NOT NULL,
    triage_explanation TEXT NOT NULL,
    triggered_rules TEXT NOT NULL,
    human_review_required INTEGER NOT NULL DEFAULT 1,
    queue_status TEXT NOT NULL DEFAULT 'Waiting',
    reviewed_by_staff INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    event_type TEXT NOT NULL,
    event_detail TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE SET NULL
);
"""

def connect(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(db_path: str | Path = DEFAULT_DB) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)

def log_event(conn: sqlite3.Connection, patient_id: int | None, event_type: str, detail: str) -> None:
    conn.execute(
        "INSERT INTO audit_events(patient_id, event_type, event_detail) VALUES (?, ?, ?)",
        (patient_id, event_type, detail[:500])
    )

def create_patient(db_path: str | Path = DEFAULT_DB, **data: Any) -> int:
    required = ["patient_code", "display_name", "age", "symptom_group", "symptoms",
                "symptom_duration", "observations", "possible_emergency_warning_sign",
                "required_information_complete", "human_review_requested", "priority",
                "triage_explanation", "triggered_rules", "human_review_required"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if not str(data["display_name"]).strip():
        raise ValueError("Display name is required.")
    age = int(data["age"])
    if not 0 <= age <= 120:
        raise ValueError("Age must be between 0 and 120.")
    with connect(db_path) as conn:
        cur = conn.execute("""
            INSERT INTO patients (
                patient_code, display_name, age, symptom_group, symptoms, symptom_duration,
                observations, possible_emergency_warning_sign, required_information_complete,
                human_review_requested, priority, triage_explanation, triggered_rules,
                human_review_required
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(data["patient_code"]), str(data["display_name"]).strip(), age,
            str(data["symptom_group"]), str(data["symptoms"]).strip(),
            str(data["symptom_duration"]), str(data.get("observations", "")),
            int(bool(data["possible_emergency_warning_sign"])),
            int(bool(data["required_information_complete"])),
            int(bool(data["human_review_requested"])), str(data["priority"]),
            str(data["triage_explanation"]), str(data["triggered_rules"]),
            int(bool(data["human_review_required"]))
        ))
        pid = int(cur.lastrowid)
        log_event(conn, pid, "patient_created", "Synthetic/demo patient record created.")
        return pid

def get_patients(db_path: str | Path = DEFAULT_DB):
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM patients ORDER BY created_at DESC, id DESC").fetchall()

def get_patient(db_path: str | Path, patient_id: int):
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()

def update_patient_status(db_path: str | Path, patient_id: int, queue_status: str | None = None,
                          reviewed_by_staff: bool | None = None) -> bool:
    allowed = {"Waiting", "In review", "Completed", "Cancelled"}
    updates, values = [], []
    if queue_status is not None:
        if queue_status not in allowed:
            raise ValueError("Invalid queue status.")
        updates.append("queue_status = ?")
        values.append(queue_status)
    if reviewed_by_staff is not None:
        updates.append("reviewed_by_staff = ?")
        values.append(int(bool(reviewed_by_staff)))
    if not updates:
        return False
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(int(patient_id))
    with connect(db_path) as conn:
        cur = conn.execute(f"UPDATE patients SET {', '.join(updates)} WHERE id = ?", values)
        if cur.rowcount:
            log_event(conn, int(patient_id), "status_updated", f"Updated fields: {', '.join(updates)}")
        return cur.rowcount > 0

def delete_patient(db_path: str | Path, patient_id: int) -> bool:
    with connect(db_path) as conn:
        log_event(conn, int(patient_id), "patient_deleted", "Record deleted from demonstration database.")
        cur = conn.execute("DELETE FROM patients WHERE id = ?", (int(patient_id),))
        return cur.rowcount > 0

def get_events(db_path: str | Path = DEFAULT_DB):
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM audit_events ORDER BY created_at DESC, id DESC").fetchall()

def seed_demo_data(db_path: str | Path = DEFAULT_DB) -> int:
    """Seed fictional examples once; never inserts real patient data."""
    with connect(db_path) as conn:
        existing = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    if existing:
        return 0
    from services.triage_engine import assess
    from datetime import datetime
    samples = [
        ("DEMO-1001", "Demo Patient A", 34, "routine_mild", "Mild, self-reported discomfort", "Today", "", False, True, False),
        ("DEMO-1002", "Demo Patient B", 52, "routine_moderate", "Persistent discomfort reported", "1–2 days", "Synthetic example only", False, True, False),
        ("DEMO-1003", "Demo Patient C", 27, "needs_review", "Unclear symptom description", "Unknown", "", False, False, True),
        ("DEMO-1004", "Demo Patient D", 63, "needs_review", "Worsening symptoms reported", "Several hours", "", False, True, True),
    ]
    count = 0
    for code, name, age, group, symptoms, duration, obs, emergency, complete, review in samples:
        result = assess(group, emergency, complete, review)
        create_patient(
            db_path, patient_code=code, display_name=name, age=age, symptom_group=group,
            symptoms=symptoms, symptom_duration=duration, observations=obs,
            possible_emergency_warning_sign=emergency, required_information_complete=complete,
            human_review_requested=review, priority=result["priority"],
            triage_explanation=result["explanation"],
            triggered_rules=";".join(result["triggered_rules"]),
            human_review_required=result["human_review_required"]
        )
        count += 1
    return count

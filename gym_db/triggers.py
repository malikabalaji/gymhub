"""Database triggers implemented with MongoDB change streams.

MongoDB has no CREATE TRIGGER statement. The supported equivalent is a change stream:
the server pushes every insert, update, replace and delete on a collection to a listening
client, which reacts to it. Change streams need a replica set, which this project uses.

Trigger TR1 (audit trail): every change to members and payments is written to the
audit_log collection with the operation, the business key, the fields that changed and
the time. This gives the administrator a tamper-evident history of who paid what and
when a membership changed (NFR3 security, NFR5 consistency).

Trigger TR2 (membership reactivation): when a payment changes to status "paid" for a
member whose membership is "expired", the member is set back to "active".

    python -m gym_db.triggers            # run the triggers until Ctrl+C
"""
import threading
from datetime import datetime, timezone

WATCHED = ["members", "payments"]


def _business_key(db, coll, event):
    doc = event.get("fullDocument") or {}
    key = doc.get("member_id") if coll == "members" else doc.get("payment_id")
    if key is None and coll == "payments" and isinstance(doc.get("member_id"), str):
        key = doc["member_id"]
    return key or str(event["documentKey"]["_id"])


def handle_event(db, event):
    """Apply both triggers to one change event."""
    coll = event["ns"]["coll"]
    op = event["operationType"]
    changed = None
    if op == "update":
        desc = event.get("updateDescription", {})
        changed = sorted(list(desc.get("updatedFields", {}).keys()) + desc.get("removedFields", []))
    # TR1 audit trail
    db.audit_log.insert_one({
        "collection": coll, "operation": op, "key": _business_key(db, coll, event),
        "changed_fields": changed, "at": datetime.now(timezone.utc),
    })
    # TR2 reactivate an expired membership once a bill is paid
    doc = event.get("fullDocument") or {}
    if coll == "payments" and op in ("update", "replace") and doc.get("status") == "paid":
        res = db.members.update_one({"_id": doc["member_id"], "membership.status": "expired"},
                                    {"$set": {"membership.status": "active"}})
        if res.modified_count:
            member = db.members.find_one({"_id": doc["member_id"]}, {"member_id": 1})
            db.audit_log.insert_one({"collection": "members", "operation": "trigger:reactivate",
                                     "key": member["member_id"], "changed_fields": ["membership.status"],
                                     "at": datetime.now(timezone.utc)})


def watch(db, stop_event=None, ready_event=None):
    """Listen to members and payments until stop_event is set."""
    pipeline = [{"$match": {"ns.coll": {"$in": WATCHED}}}]
    with db.watch(pipeline, full_document="updateLookup", max_await_time_ms=200) as stream:
        if ready_event:
            ready_event.set()
        while stop_event is None or not stop_event.is_set():
            event = stream.try_next()
            if event is not None:
                handle_event(db, event)


def start_in_background(db):
    """Start the triggers on a daemon thread; returns the stop event."""
    stop, ready = threading.Event(), threading.Event()
    threading.Thread(target=watch, args=(db, stop, ready), daemon=True).start()
    ready.wait(5)
    return stop


if __name__ == "__main__":
    from gym_db.config import get_db
    print("Triggers TR1 (audit trail) and TR2 (reactivation) are running. Press Ctrl+C to stop.")
    try:
        watch(get_db())
    except KeyboardInterrupt:
        pass

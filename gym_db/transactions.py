"""Step 6: multi-document ACID transactions.

Transactions need a replica set (a single-node replica set is enough; see README).
Two business operations touch several collections and must be all-or-nothing:

T1 renew_membership: insert a paid payment AND extend the member's end date.
T2 close_session:    insert attendance rows for a session AND mark it completed.
"""
from datetime import timedelta

from pymongo import ReadPreference
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from .config import REFERENCE_DATE, TIER_FEES, get_client, is_mock


class TransactionAborted(Exception):
    pass


def _run(db, fn):
    """Run fn(session) inside a transaction, with automatic retry on transient errors.
    Under mongomock (no transaction support) fn runs without a session."""
    if is_mock():
        return fn(None)
    client = get_client()
    with client.start_session() as s:
        return s.with_transaction(
            fn,
            read_concern=ReadConcern("snapshot"),
            write_concern=WriteConcern("majority"),
            read_preference=ReadPreference.PRIMARY,
        )


def renew_membership(db, member_id, months, mode="UPI", fail_midway=False):
    """T1. fail_midway=True raises after the payment insert to prove the rollback."""
    def txn(s):
        m = db.members.find_one({"member_id": member_id}, session=s)
        if not m:
            raise TransactionAborted(f"{member_id} not found")
        fee = TIER_FEES[m["membership"]["type"]] * months
        old_end = m["membership"]["end_date"]
        start = max(old_end, REFERENCE_DATE) + timedelta(days=1)
        new_end = start + timedelta(days=30 * months)
        last = db.payments.find_one({}, sort=[("payment_id", -1)], projection={"payment_id": 1}, session=s)
        pid = f"PAY{int(last['payment_id'][3:]) + 1}"
        db.payments.insert_one({
            "payment_id": pid, "member_id": m["_id"], "member_name": m["name"], "amount": fee,
            "currency": "INR", "payment_mode": mode, "status": "paid",
            "billing_period_start": start, "billing_period_end": new_end,
            "payment_date": REFERENCE_DATE, "due_date": REFERENCE_DATE}, session=s)
        if fail_midway:
            raise TransactionAborted("Simulated failure after payment insert")
        db.members.update_one({"_id": m["_id"]},
                              {"$set": {"membership.end_date": new_end, "membership.status": "active"}},
                              session=s)
        return {"payment_id": pid, "amount": fee, "new_end_date": new_end.date().isoformat()}
    return _run(db, txn)


def close_session(db, session_id, marks):
    """T2. marks = {member_id: (status, check_in_time)}. Everything commits together."""
    def txn(s):
        sess = db.class_sessions.find_one({"session_id": session_id, "status": "scheduled"}, session=s)
        if not sess:
            raise TransactionAborted(f"{session_id} is not an open session")
        cls = db.classes.find_one({"_id": sess["class_id"]}, session=s)
        roster = {e["member_id"]: e["member_name"] for e in cls["enrolled_members"]}
        ids = {d["member_id"]: d["_id"] for d in
               db.members.find({"member_id": {"$in": list(marks)}}, {"member_id": 1}, session=s)}
        db.class_sessions.update_one({"_id": sess["_id"]}, {"$set": {"status": "completed"}}, session=s)
        rows = 0
        for mid, (status, t) in marks.items():
            oid = ids.get(mid)
            if oid not in roster:  # fails AFTER earlier writes: the rollback undoes them all
                raise TransactionAborted(f"{mid} is not enrolled in {cls['class_name']}")
            db.attendance.insert_one({"session_id": sess["_id"], "class_id": sess["class_id"],
                                      "member_id": oid, "member_name": roster[oid], "date": sess["date"],
                                      "status": status, "check_in_time": t}, session=s)
            rows += 1
        return {"session_id": session_id, "attendance_rows": rows}
    return _run(db, txn)

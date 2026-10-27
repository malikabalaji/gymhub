"""Review 2 intermediate demonstration.

    python demo.py            # against MongoDB (MONGO_URI, default localhost replica set rs0)
    python demo.py --mock     # offline, in-memory mongomock (no server needed)
    python demo.py --section crud   # run one section: setup | crud | agg | graph | index | txn | trig

Runs every step in order: implementation, CRUD, advanced features, triggers.
"""
import argparse
from datetime import datetime
from pprint import pformat

from pymongo.errors import DuplicateKeyError, WriteError

from gym_db import aggregations as A, crud as C, transactions as T, triggers as TR
from gym_db.config import COLLECTIONS, REFERENCE_DATE, get_db, is_mock, supports_transactions
from gym_db.indexes import create_indexes, explain_comparison
from gym_db.schema import create_collections
from gym_db.seed import seed


def h1(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def h2(t):
    print(f"\n--- {t}")


def show(x, width=100):
    print(pformat(x, width=width, sort_dicts=False))


def table(rows, cols):
    if not rows:
        print("(no rows)")
        return
    w = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("  ".join(c.ljust(w[c]) for c in cols))
    print("  ".join("-" * w[c] for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(w[c]) for c in cols))


# ---------------------------------------------------------------- 1. IMPLEMENTATION
def setup(db):
    h1("1. DATABASE IMPLEMENTATION: collections, validators, sample data, indexes")
    create_collections(db)
    print("Collections created with $jsonSchema validators:" + (" (skipped under mongomock)" if is_mock() else ""))
    print("  " + ", ".join(COLLECTIONS))
    counts = seed(db)
    h2("Sample data loaded (document counts)")
    table([{"collection": k, "documents": v} for k, v in counts.items()] +
          [{"collection": "TOTAL", "documents": sum(counts.values())}], ["collection", "documents"])
    idx = create_indexes(db)
    h2(f"{len(idx)} indexes created")
    print("  " + ", ".join(idx))

    h2("Relationship check: one member resolved across all referenced collections")
    m = db.members.find_one({"member_id": "MEM1001"})
    t = db.trainers.find_one({"_id": m["assigned_trainer_id"]})
    print(f"{m['member_id']} {m['name']} ({m['membership']['type']}) -> trainer {t['trainer_id']} {t['name']}")
    print(f"  workout plans: {db.workout_plans.count_documents({'member_id': m['_id']})}"
          f" | classes: {db.classes.count_documents({'enrolled_members.member_id': m['_id']})}"
          f" | attendance rows: {db.attendance.count_documents({'member_id': m['_id']})}"
          f" | payments: {db.payments.count_documents({'member_id': m['_id']})}")

    if not is_mock():
        h2("Validator in action: inserting a member with an invalid tier")
        try:
            db.members.insert_one({"member_id": "MEM9999", "name": "Bad Data", "email": "bad@x.com",
                                   "password_hash": "x", "role": "member",
                                   "membership": {"type": "Gold", "status": "active",
                                                  "start_date": REFERENCE_DATE, "end_date": REFERENCE_DATE}})
        except WriteError as e:
            print(f"REJECTED by validator: {e.code} Document failed validation")


# ---------------------------------------------------------------- 2. CRUD
def crud(db):
    h1("2. CRUD OPERATIONS")

    h2("CREATE: new trainer, new member (referred by MEM1003), workout plan, class, session, invoice")
    tid = C.create_trainer(db, "Nisha Varghese", "nisha.v@gym.com", "9845099999", "Trainer@09",
                           ["Kickboxing", "HIIT"], "NASM-CPT", 5)
    mid = C.create_member(db, "Rhea Thomas", "rhea.thomas@example.com", "9876501234",
                          datetime(2004, 3, 15), "Female", "Rhea@2026", tier="Premium",
                          trainer_id=tid, referred_by="MEM1003")
    pid = C.create_workout_plan(db, mid, "Muscle Gain", 8, [
        {"day": "Mon", "exercise_name": "Squat", "sets": 4, "reps": 10, "weight_kg": 30, "notes": ""},
        {"day": "Wed", "exercise_name": "Bench Press", "sets": 4, "reps": 10, "weight_kg": 25, "notes": ""},
    ])
    cid = C.create_class(db, "Kickboxing Basics", "Kickboxing", tid, 2,
                         [{"day_of_week": "Thu", "start_time": "18:00", "end_time": "19:00", "room": "B2"}])
    sid = C.create_session(db, cid, datetime(2026, 10, 1), "18:00", "19:00")
    inv = C.create_invoice(db, mid, datetime(2026, 10, 1), datetime(2026, 10, 31), datetime(2026, 10, 5))
    print(f"trainer {tid} | member {mid} | plan {pid} | class {cid} | session {sid} | invoice {inv}")

    h2("CREATE rejected: duplicate email (unique index uq_email)")
    try:
        C.create_member(db, "Duplicate", "rhea.thomas@example.com", "9000000000",
                        datetime(2000, 1, 1), "Female", "x")
    except DuplicateKeyError:
        print("DuplicateKeyError: email already registered")

    h2("CREATE rejected: member assigned to a trainer that does not exist (app-level integrity)")
    try:
        C.create_member(db, "Ghost", "ghost@example.com", "9000000001", datetime(2000, 1, 1),
                        "Male", "x", trainer_id="TRN77")
    except C.IntegrityError as e:
        print(f"IntegrityError: {e}")

    h2(f"READ: member profile {mid} (password_hash excluded by projection)")
    show(C.get_member(db, mid))
    h2("READ: VIP members, page 1 (filter + sort + skip/limit pagination)")
    rows, total = C.list_members(db, tier="VIP", status="active", page=1, page_size=5)
    print(f"{total} active VIP members; first 5:")
    table([{"member_id": r["member_id"], "name": r["name"], "city": r["address"]["city"]} for r in rows],
          ["member_id", "name", "city"])
    h2("READ: trainers who teach Yoga (query inside embedded array)")
    table(C.find_trainers_by_skill(db, "Yoga"), ["trainer_id", "name"])
    h2("READ: MEM1001 last 5 attendance records (uses index ix_member_date)")
    table(C.attendance_history(db, "MEM1001"), ["date", "status", "check_in_time"])

    h2("UPDATE: enroll into a class of capacity 2 (atomic capacity guard)")
    C.enroll_member(db, cid, mid)
    C.enroll_member(db, cid, "MEM1002") if db.members.find_one(
        {"member_id": "MEM1002", "membership.status": "active"}) else C.enroll_member(db, cid, "MEM1004")
    on_roster = {e["member_id"] for e in C.get_class(db, cid)["enrolled_members"]}
    third = next(m["member_id"] for m in db.members.find({"membership.status": "active"}).sort("member_id", 1)
                 if m["_id"] not in on_roster)
    try:
        C.enroll_member(db, cid, third)
    except C.IntegrityError as e:
        print(f"3rd enrollment blocked -> {e}")
    print("roster:", [e["member_name"] for e in C.get_class(db, cid)["enrolled_members"]])

    h2("UPDATE: embedded arrays ($push, positional $inc, $addToSet, $pull)")
    C.add_exercise(db, pid, {"day": "Fri", "exercise_name": "Deadlift", "sets": 3, "reps": 8,
                             "weight_kg": 40, "notes": "focus on form"})
    C.progress_exercise(db, pid, "Squat", 5)
    C.add_specialization(db, tid, "Boxing")
    C.add_specialization(db, tid, "Boxing")  # second call is a no-op thanks to $addToSet
    table(C.get_active_plan(db, mid)["exercises"], ["day", "exercise_name", "sets", "reps", "weight_kg"])
    print("specialization:", C.get_trainer(db, tid)["specialization"])

    h2("UPDATE: tier upgrade Premium -> VIP, and name change propagated to denormalized copies")
    C.change_membership(db, mid, tier="VIP")
    C.update_member(db, mid, name="Rhea T. Thomas")
    oid = db.members.find_one({"member_id": mid})["_id"]
    print("members:", C.get_member(db, mid)["name"], "| tier:", C.get_member(db, mid)["membership"]["type"])
    print("workout_plans.member_name:", db.workout_plans.find_one({"member_id": oid})["member_name"])
    print("payments.member_name:", db.payments.find_one({"member_id": oid})["member_name"])
    print("classes.enrolled_members.member_name:",
          [e["member_name"] for e in C.get_class(db, cid)["enrolled_members"] if e["member_id"] == oid])

    h2("UPDATE: attendance upsert (mark late, then correct to present; still one row)")
    C.mark_attendance(db, sid, mid, "late", "18:09")
    C.mark_attendance(db, sid, mid, "present", "17:58")
    s_oid = db.class_sessions.find_one({"session_id": sid})["_id"]
    print(f"rows for ({sid}, {mid}):", db.attendance.count_documents({"session_id": s_oid, "member_id": oid}),
          "| status:", db.attendance.find_one({"session_id": s_oid, "member_id": oid})["status"])

    h2("UPDATE: payments (record payment, overdue sweep)")
    print("record_payment:", C.record_payment(db, inv, "UPI"))
    print("bills newly flagged overdue by sweep:", C.flag_overdue(db))

    h2("DELETE: remove exercise, withdraw from class, delete attendance, delete member with cascade")
    C.remove_exercise(db, pid, "Deadlift")
    print("exercises now:", [e["exercise_name"] for e in C.get_active_plan(db, mid)["exercises"]])
    print("withdraw:", C.withdraw_member(db, cid, mid), "| delete attendance:", C.delete_attendance(db, sid, mid))
    debtor = db.payments.find_one({"status": "overdue"})
    dm = db.members.find_one({"_id": debtor["member_id"]})["member_id"]
    try:
        C.delete_member(db, dm)
    except C.IntegrityError as e:
        print(f"delete {dm} blocked -> {e}")
    print(f"delete {mid} ->", C.delete_member(db, mid))
    print("member still exists?", C.get_member(db, mid) is not None,
          "| orphan plans left:", db.workout_plans.count_documents({"member_id": oid}))
    try:
        C.delete_trainer(db, "TRN01")
    except C.IntegrityError as e:
        print(f"delete TRN01 blocked -> {e}")

    h2("AUTH (FR8): bcrypt login check")
    print("correct password:", C.authenticate(db, "priya.menon@gym.com", "Trainer@01"))
    print("wrong password:  ", C.authenticate(db, "priya.menon@gym.com", "wrong"))


# ---------------------------------------------------------------- 3. ADVANCED
def agg(db):
    h1("3a. AGGREGATION PIPELINES (FR7)")
    h2("A1 Monthly revenue trend by tier (paid only)")
    for r in A.revenue_trend(db):
        tiers = ", ".join(f"{t['tier']} {t['revenue']:,}" for t in sorted(r["by_tier"], key=lambda x: x["tier"]))
        print(f"{r['month']}  INR {r['total_revenue']:>8,}  ({r['payments']} payments)  [{tiers}]")
    h2("A2 Class popularity")
    table(A.class_popularity(db), ["class_name", "trainer", "enrolled", "capacity", "fill_rate_pct",
                                   "sessions_held", "avg_turnout", "attendance_rate_pct"])
    h2("A3 Members at risk (attendance < 60%)")
    table(A.at_risk_members(db), ["member_id", "name", "tier", "sessions_marked", "attended", "rate_pct"])
    h2("A4 Outstanding dues (collections worklist)")
    table(A.outstanding_dues(db)[:12], ["member_id", "name", "tier", "bills", "amount_due",
                                        "max_days_overdue", "priority"])
    h2("A5 Trainer workload (3 x $lookup)")
    table(A.trainer_workload(db), ["trainer_id", "name", "members", "active_plans", "classes"])
    h2("A6 Membership overview ($facet + $bucket in one query)")
    show(A.membership_overview(db))
    h2("A7 Most prescribed exercises ($unwind embedded array)")
    table(A.top_exercises(db), ["exercise", "plans", "avg_sets", "avg_weight_kg"])
    h2("A8 Peak check-in hours")
    table(A.peak_hours(db)[:6], ["hour", "check_ins"])
    h2("V1 member_dashboard view" + (" (pipeline run directly under mongomock)" if is_mock() else ""))
    A.create_views(db)
    show(A.member_dashboard(db, "MEM1005"))


def graph(db):
    h1("3b. GRAPH TRAVERSAL: referral network with $graphLookup")
    h2("G2 Top referrers (size of downstream network)")
    top = A.top_referrers(db)
    table(top, ["member_id", "name", "direct", "network_size", "levels"])
    if top:
        h2(f"G1 Full referral tree of {top[0]['member_id']}")
        net = A.referral_network(db, top[0]["member_id"])
        for n in net["network"]:
            print("  " * n["level"] + f"L{n['level']} {n['member_id']} {n['name']}")


def index(db):
    h1("3c. INDEXING")
    h2("Indexes on attendance and payments")
    for coll in ("attendance", "payments"):
        for name, info in db[coll].index_information().items():
            extra = " (partial)" if "partialFilterExpression" in info else ""
            extra += " (unique)" if info.get("unique") else ""
            print(f"  {coll}.{name}: {info['key']}{extra}")
    h2("explain(): member attendance history, collection scan vs index scan")
    ex = explain_comparison(db)
    if ex:
        table([{"plan": k, **v} for k, v in ex.items()],
              ["plan", "stage", "docs_examined", "keys_examined", "returned", "time_ms"])
    else:
        print("(explain() needs a real MongoDB server; skipped under mongomock)")
    if not is_mock():
        h2("Text index search: classes matching 'yoga'")
        table(list(db.classes.find({"$text": {"$search": "yoga"}}, {"_id": 0, "class_name": 1, "category": 1})),
              ["class_name", "category"])


def txn(db):
    h1("3d. MULTI-DOCUMENT ACID TRANSACTIONS")
    if not is_mock() and not supports_transactions(db):
        print("This server is a standalone mongod. Transactions need a replica set: see README section 2.")
        return
    if is_mock():
        print("(mongomock has no transactions: operations run without a session; rollback demo skipped)")
    m = "MEM1010"
    before = db.members.find_one({"member_id": m})["membership"]["end_date"].date()
    pay_before = db.payments.count_documents({})
    if not is_mock():
        h2("T1 renew_membership with a simulated failure -> rollback")
        try:
            T.renew_membership(db, m, 3, fail_midway=True)
        except T.TransactionAborted as e:
            print(f"aborted: {e}")
        print(f"payments count {pay_before} -> {db.payments.count_documents({})} (unchanged)",
              f"| end_date still {db.members.find_one({'member_id': m})['membership']['end_date'].date()}")
    h2("T1 renew_membership, 3 months -> commit")
    print(T.renew_membership(db, m, 3))
    print(f"end_date {before} -> {db.members.find_one({'member_id': m})['membership']['end_date'].date()}",
          f"| payments {pay_before} -> {db.payments.count_documents({})}")

    h2("T2 close_session: attendance rows + session status in one transaction")
    s = db.class_sessions.find_one({"status": "scheduled"}, sort=[("date", 1), ("session_id", 1)])
    roster = db.classes.find_one({"_id": s["class_id"]})["enrolled_members"][:3]
    ids = {d["_id"]: d["member_id"] for d in db.members.find({"_id": {"$in": [r["member_id"] for r in roster]}})}
    marks = {ids[r["member_id"]]: st for r, st in zip(roster, [("present", "06:58"), ("late", "07:09"),
                                                               ("absent", None)])}
    print(f"{s['session_id']} {s['class_name']} {s['date'].date()}:", T.close_session(db, s["session_id"], marks))
    print("session status now:", db.class_sessions.find_one({"_id": s["_id"]})["status"])
    if not is_mock():
        h2("T2 with a member not on the roster -> whole transaction rolled back")
        s2 = db.class_sessions.find_one({"status": "scheduled"}, sort=[("date", 1), ("session_id", 1)])
        n_before = db.attendance.count_documents({})
        roster2 = db.classes.find_one({"_id": s2["class_id"]})["enrolled_members"][:1]
        good = db.members.find_one({"_id": roster2[0]["member_id"]})["member_id"]
        outsider = db.members.find_one({"_id": {"$nin": [e["member_id"] for e in
                                        db.classes.find_one({"_id": s2["class_id"]})["enrolled_members"]]}})["member_id"]
        try:
            T.close_session(db, s2["session_id"], {good: ("present", None), outsider: ("present", None)})
        except T.TransactionAborted as e:
            print(f"aborted: {e}")
        print(f"attendance rows {n_before} -> {db.attendance.count_documents({})}",
              f"| {s2['session_id']} status: {db.class_sessions.find_one({'_id': s2['_id']})['status']}")


def trig(db):
    h1("3e. TRIGGERS: change streams on members and payments")
    if is_mock() or not supports_transactions(db):
        print("(change streams need a real replica set; skipped)")
        return
    import time
    db.audit_log.drop()
    stop = TR.start_in_background(db)
    expired = db.members.find_one({"membership.status": "expired"}, sort=[("member_id", 1)])
    inv = C.create_invoice(db, expired["member_id"], datetime(2026, 10, 1), datetime(2026, 10, 31), datetime(2026, 10, 5))
    C.record_payment(db, inv, "UPI")
    C.update_member(db, "MEM1002", phone="9000000002")
    time.sleep(1.5)
    stop.set()
    h2(f"TR2: {expired['member_id']} was expired; after paying {inv} the trigger set status to "
       f"{db.members.find_one({'_id': expired['_id']})['membership']['status']}")
    h2("TR1: audit_log written by the trigger")
    table([{**r, "changed_fields": ", ".join(r["changed_fields"] or [])} for r in
           db.audit_log.find({}, {"_id": 0, "at": 0}).sort("at", 1)],
          ["collection", "operation", "key", "changed_fields"])


SECTIONS = {"setup": setup, "crud": crud, "agg": agg, "graph": graph, "index": index, "txn": txn, "trig": trig}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="use in-memory mongomock instead of a server")
    ap.add_argument("--section", choices=list(SECTIONS), help="run only one section (setup is always run first)")
    args = ap.parse_args()
    db = get_db(mock=args.mock)
    print(f"Connected to {'mongomock (in-memory)' if is_mock() else 'MongoDB'}; database '{db.name}';"
          f" reference date {REFERENCE_DATE.date()}")
    if args.section == "setup":
        setup(db)
    elif args.section:
        setup(db)
        SECTIONS[args.section](db)
    else:
        for fn in SECTIONS.values():
            fn(db)
    print("\nDemo complete.")

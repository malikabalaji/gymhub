"""Index performance benchmark at scale (Chapter 6.2 of the final report).

Builds a separate database, gym_bench, with synthetic attendance and payment documents
shaped exactly like gym_db, then runs three report queries three ways:
  1. forced collection scan        hint({$natural: 1})
  2. with the index gym_db uses
  3. (payments only) with a full index instead of the partial index
and reports documents examined, index keys examined and median execution time.

    python benchmark.py                   # default: 200,000 attendance rows, 60,000 payments
    python benchmark.py --attendance 50000 --payments 20000
Needs a real MongoDB server; timings depend on the machine.
"""
import argparse
import random
import statistics
import time
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, MongoClient

from gym_db.config import MONGO_URI

TODAY = datetime(2026, 9, 24)


def build(db, n_att, n_pay, members=2000, classes=40):
    rng = random.Random(7)
    db.attendance.drop()
    db.payments.drop()
    mids = [ObjectId() for _ in range(members)]
    cids = [ObjectId() for _ in range(classes)]
    start = datetime(2025, 1, 1)
    batch = []
    for i in range(n_att):
        r = rng.random()
        batch.append({"session_id": ObjectId(), "class_id": rng.choice(cids), "member_id": rng.choice(mids),
                      "member_name": "x", "date": start + timedelta(days=rng.randint(0, 630)),
                      "status": "present" if r < 0.72 else ("late" if r < 0.8 else "absent"),
                      "check_in_time": "18:00"})
        if len(batch) == 10000:
            db.attendance.insert_many(batch)
            batch = []
    if batch:
        db.attendance.insert_many(batch)
    batch = []
    for i in range(n_pay):
        due = start + timedelta(days=rng.randint(0, 640))
        r = rng.random()
        status = "paid" if due < TODAY and r < 0.95 else ("overdue" if due < TODAY else "pending")
        batch.append({"payment_id": f"P{i}", "member_id": rng.choice(mids), "member_name": "x",
                      "amount": rng.choice([1500, 2500, 4000]), "currency": "INR", "status": status,
                      "due_date": due})
    db.payments.insert_many(batch)
    return mids, cids


def measure(coll, query, sort=None, hint=None, runs=5):
    def cursor():
        c = coll.find(query)
        if sort:
            c = c.sort(sort)
        if hint:
            c = c.hint(hint)
        return c
    ex = cursor().explain()["executionStats"]
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        list(cursor())
        times.append((time.perf_counter() - t0) * 1000)
    return {"docs_examined": ex["totalDocsExamined"], "keys_examined": ex["totalKeysExamined"],
            "returned": ex["nReturned"], "median_ms": round(statistics.median(times), 2)}


def index_size(db, coll, name):
    stats = db.command("collStats", coll)
    return round(stats["indexSizes"].get(name, 0) / 1024, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attendance", type=int, default=200000)
    ap.add_argument("--payments", type=int, default=60000)
    args = ap.parse_args()
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["gym_bench"]
    print(f"MongoDB {client.server_info()['version']}: building gym_bench with "
          f"{args.attendance:,} attendance and {args.payments:,} payment documents ...")
    mids, cids = build(db, args.attendance, args.payments)
    db.attendance.create_index([("member_id", ASCENDING), ("date", DESCENDING)], name="ix_member_date")
    db.attendance.create_index([("class_id", ASCENDING), ("status", ASCENDING)], name="ix_class_status")
    db.payments.create_index([("status", ASCENDING), ("due_date", ASCENDING)], name="px_unpaid_dues",
                             partialFilterExpression={"status": {"$in": ["pending", "overdue"]}})
    db.payments.create_index([("status", ASCENDING), ("due_date", ASCENDING), ("_id", ASCENDING)],
                             name="ix_status_due_full")

    member, cls = mids[17], cids[3]
    rows = [
        ("B1 member attendance history", "COLLSCAN",
         measure(db.attendance, {"member_id": member}, [("date", -1)], [("$natural", 1)])),
        ("B1 member attendance history", "ix_member_date",
         measure(db.attendance, {"member_id": member}, [("date", -1)], "ix_member_date")),
        ("B2 absentees of one class", "COLLSCAN",
         measure(db.attendance, {"class_id": cls, "status": "absent"}, None, [("$natural", 1)])),
        ("B2 absentees of one class", "ix_class_status",
         measure(db.attendance, {"class_id": cls, "status": "absent"}, None, "ix_class_status")),
    ]
    unpaid = {"status": {"$in": ["pending", "overdue"]}, "due_date": {"$lt": TODAY}}
    rows += [
        ("B3 overdue dues report", "COLLSCAN", measure(db.payments, unpaid, None, [("$natural", 1)])),
        ("B3 overdue dues report", "px_unpaid_dues (partial)", measure(db.payments, unpaid, None, "px_unpaid_dues")),
        ("B3 overdue dues report", "full index", measure(db.payments, unpaid, None, "ix_status_due_full")),
    ]
    w = max(len(r[0]) for r in rows), max(len(r[1]) for r in rows)
    print(f"\n{'query'.ljust(w[0])}  {'plan'.ljust(w[1])}  docs_examined  keys_examined  returned  median_ms")
    for q, plan, m in rows:
        print(f"{q.ljust(w[0])}  {plan.ljust(w[1])}  {m['docs_examined']:>13,}  {m['keys_examined']:>13,}  "
              f"{m['returned']:>8,}  {m['median_ms']:>9}")
    print(f"\nIndex size: px_unpaid_dues {index_size(db, 'payments', 'px_unpaid_dues')} KB "
          f"vs full index {index_size(db, 'payments', 'ix_status_due_full')} KB")
    client.drop_database("gym_bench")


if __name__ == "__main__":
    main()

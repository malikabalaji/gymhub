"""Representative query set for the final report (Chapter 6 and Appendix D).

Every query is stored as data (collection + filter or pipeline) together with its SQL
equivalent, so the same definition is used to run it, to print its output, and to
generate the mongosh version in mongosh/queries.js.

    python queries.py                 # run all queries against MongoDB (recreates gym_db)
    python queries.py --mock          # run without a server (in-memory)
    python queries.py --only Q11      # run one query
    python queries.py --export-js     # (re)write mongosh/ddl.js and mongosh/queries.js
"""
import argparse
import json
from datetime import datetime

from gym_db.config import REFERENCE_DATE, get_db, is_mock
from gym_db.indexes import INDEXES, create_indexes
from gym_db.schema import VALIDATORS, create_collections
from gym_db.seed import seed

UNPAID = ["pending", "overdue"]

QUERIES = [
    # ------------------------------------------------------------------ SELECTION
    {
        "id": "Q1", "category": "Selection",
        "title": "Active VIP members living in Chennai",
        "sql": "SELECT member_id, name, end_date FROM members\n"
               "WHERE tier = 'VIP' AND status = 'active' AND city = 'Chennai'\n"
               "ORDER BY member_id;",
        "collection": "members", "op": "find",
        "filter": {"membership.type": "VIP", "membership.status": "active", "address.city": "Chennai"},
        "projection": {"_id": 0, "member_id": 1, "name": 1, "membership.end_date": 1},
        "sort": [("member_id", 1)],
    },
    {
        "id": "Q2", "category": "Selection",
        "title": "Trainers who teach Yoga or CrossFit with at least 6 years of experience",
        "sql": "SELECT DISTINCT t.trainer_id, t.name, t.experience_years\n"
               "FROM trainers t JOIN trainer_specializations s ON s.trainer_id = t.trainer_id\n"
               "WHERE s.skill IN ('Yoga', 'CrossFit') AND t.experience_years >= 6\n"
               "ORDER BY t.experience_years DESC;",
        "collection": "trainers", "op": "find",
        "filter": {"specialization": {"$in": ["Yoga", "CrossFit"]}, "experience_years": {"$gte": 6}},
        "projection": {"_id": 0, "trainer_id": 1, "name": 1, "specialization": 1, "experience_years": 1},
        "sort": [("experience_years", -1)],
    },
    {
        "id": "Q3", "category": "Selection",
        "title": "Unpaid bills already past their due date (oldest first)",
        "sql": "SELECT payment_id, member_name, amount, status, due_date FROM payments\n"
               "WHERE status IN ('pending', 'overdue') AND due_date < DATE '2026-09-24'\n"
               "ORDER BY due_date, payment_id LIMIT 8;",
        "collection": "payments", "op": "find",
        "filter": {"status": {"$in": UNPAID}, "due_date": {"$lt": REFERENCE_DATE}},
        "projection": {"_id": 0, "payment_id": 1, "member_name": 1, "amount": 1, "status": 1, "due_date": 1},
        "sort": [("due_date", 1), ("payment_id", 1)], "limit": 8, "count": True,
    },
    # ------------------------------------------------------------------ JOINS
    {
        "id": "Q4", "category": "Join (inner)",
        "title": "Active VIP members with their assigned trainer",
        "sql": "SELECT m.member_id, m.name, t.name AS trainer, t.certification\n"
               "FROM members m INNER JOIN trainers t ON t.trainer_pk = m.assigned_trainer_id\n"
               "WHERE m.tier = 'VIP' AND m.status = 'active'\n"
               "ORDER BY m.member_id LIMIT 8;",
        "collection": "members", "op": "aggregate",
        "pipeline": [
            {"$match": {"membership.type": "VIP", "membership.status": "active"}},
            {"$lookup": {"from": "trainers", "localField": "assigned_trainer_id",
                         "foreignField": "_id", "as": "t"}},
            {"$unwind": "$t"},
            {"$project": {"_id": 0, "member_id": 1, "name": 1, "trainer": "$t.name",
                          "certification": "$t.certification"}},
            {"$sort": {"member_id": 1}},
            {"$limit": 8},
        ],
    },
    {
        "id": "Q5", "category": "Join (three tables)",
        "title": "Attendance history of MEM1001 with class name and session time",
        "sql": "SELECT s.date, c.class_name, s.start_time, a.status, a.check_in_time\n"
               "FROM members m\n"
               "JOIN attendance a ON a.member_id = m.member_pk\n"
               "JOIN class_sessions s ON s.session_pk = a.session_id\n"
               "JOIN classes c ON c.class_pk = a.class_id\n"
               "WHERE m.member_id = 'MEM1001' ORDER BY s.date DESC;",
        "collection": "members", "op": "aggregate",
        "pipeline": [
            {"$match": {"member_id": "MEM1001"}},
            {"$lookup": {"from": "attendance", "localField": "_id", "foreignField": "member_id", "as": "a"}},
            {"$unwind": "$a"},
            {"$lookup": {"from": "class_sessions", "localField": "a.session_id", "foreignField": "_id", "as": "s"}},
            {"$unwind": "$s"},
            {"$lookup": {"from": "classes", "localField": "a.class_id", "foreignField": "_id", "as": "c"}},
            {"$unwind": "$c"},
            {"$project": {"_id": 0, "date": "$s.date", "class_name": "$c.class_name",
                          "start_time": "$s.start_time", "status": "$a.status",
                          "check_in_time": "$a.check_in_time"}},
            {"$sort": {"date": -1}},
        ],
    },
    {
        "id": "Q6", "category": "Join (left outer)",
        "title": "Every trainer with the number of classes they teach, including trainers with none",
        "sql": "SELECT t.trainer_id, t.name, COUNT(c.class_id) AS classes\n"
               "FROM trainers t LEFT OUTER JOIN classes c ON c.trainer_id = t.trainer_pk\n"
               "GROUP BY t.trainer_id, t.name ORDER BY classes DESC, t.trainer_id;",
        "collection": "trainers", "op": "aggregate",
        "pipeline": [
            {"$lookup": {"from": "classes", "localField": "_id", "foreignField": "trainer_id", "as": "c"}},
            {"$project": {"_id": 0, "trainer_id": 1, "name": 1, "classes": {"$size": "$c"},
                          "class_names": "$c.class_name"}},
            {"$sort": {"classes": -1, "trainer_id": 1}},
        ],
    },
    # ------------------------------------------------------------------ GROUPING AND AGGREGATION
    {
        "id": "Q7", "category": "Grouping and aggregation",
        "title": "Money collected by payment mode (COUNT, SUM, AVG)",
        "sql": "SELECT payment_mode, COUNT(*) AS payments, SUM(amount) AS total, AVG(amount) AS average\n"
               "FROM payments WHERE status = 'paid'\n"
               "GROUP BY payment_mode ORDER BY total DESC;",
        "collection": "payments", "op": "aggregate",
        "pipeline": [
            {"$match": {"status": "paid"}},
            {"$group": {"_id": "$payment_mode", "payments": {"$sum": 1}, "total": {"$sum": "$amount"},
                        "average": {"$avg": "$amount"}}},
            {"$project": {"_id": 0, "payment_mode": "$_id", "payments": "$payments", "total": "$total",
                          "average": {"$round": ["$average", 0]}}},
            {"$sort": {"total": -1}},
        ],
    },
    {
        "id": "Q8", "category": "Grouping with HAVING",
        "title": "Cities with more than 10 members, split by tier",
        "sql": "SELECT city, COUNT(*) AS members,\n"
               "       SUM(CASE WHEN tier = 'VIP' THEN 1 ELSE 0 END) AS vip\n"
               "FROM members GROUP BY city HAVING COUNT(*) > 10 ORDER BY members DESC;",
        "collection": "members", "op": "aggregate",
        "pipeline": [
            {"$group": {"_id": "$address.city", "members": {"$sum": 1},
                        "basic": {"$sum": {"$cond": [{"$eq": ["$membership.type", "Basic"]}, 1, 0]}},
                        "premium": {"$sum": {"$cond": [{"$eq": ["$membership.type", "Premium"]}, 1, 0]}},
                        "vip": {"$sum": {"$cond": [{"$eq": ["$membership.type", "VIP"]}, 1, 0]}}}},
            {"$match": {"members": {"$gt": 10}}},
            {"$project": {"_id": 0, "city": "$_id", "members": "$members", "basic": "$basic",
                          "premium": "$premium", "vip": "$vip"}},
            {"$sort": {"members": -1}},
        ],
    },
    {
        "id": "Q9", "category": "Grouping and aggregation",
        "title": "Attendance outcome by class category",
        "sql": "SELECT c.category, COUNT(*) AS marked,\n"
               "       SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) AS present,\n"
               "       SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) AS late,\n"
               "       SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS absent\n"
               "FROM attendance a JOIN classes c ON c.class_pk = a.class_id\n"
               "GROUP BY c.category ORDER BY marked DESC;",
        "collection": "attendance", "op": "aggregate",
        "pipeline": [
            {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "c"}},
            {"$unwind": "$c"},
            {"$group": {"_id": "$c.category", "marked": {"$sum": 1},
                        "present": {"$sum": {"$cond": [{"$eq": ["$status", "present"]}, 1, 0]}},
                        "late": {"$sum": {"$cond": [{"$eq": ["$status", "late"]}, 1, 0]}},
                        "absent": {"$sum": {"$cond": [{"$eq": ["$status", "absent"]}, 1, 0]}}}},
            {"$project": {"_id": 0, "category": "$_id", "marked": "$marked", "present": "$present",
                          "late": "$late", "absent": "$absent"}},
            {"$sort": {"marked": -1}},
        ],
    },
    # ------------------------------------------------------------------ SUBQUERIES
    {
        "id": "Q10", "category": "Subquery (scalar)",
        "title": "Members whose attendance rate is below the gym-wide average",
        "sql": "SELECT member_id, AVG(CASE WHEN status <> 'absent' THEN 100 ELSE 0 END) AS rate\n"
               "FROM attendance GROUP BY member_id\n"
               "HAVING rate < (SELECT AVG(CASE WHEN status <> 'absent' THEN 100 ELSE 0 END)\n"
               "               FROM attendance)\n"
               "ORDER BY rate LIMIT 8;",
        "collection": "attendance", "op": "aggregate",
        "pipeline": [
            {"$addFields": {"attended": {"$cond": [{"$eq": ["$status", "absent"]}, 0, 100]}}},
            {"$facet": {
                "overall": [{"$group": {"_id": None, "avg": {"$avg": "$attended"}}}],
                "per_member": [{"$group": {"_id": "$member_name", "rate": {"$avg": "$attended"},
                                           "marked": {"$sum": 1}}}],
            }},
            {"$unwind": "$overall"},
            {"$unwind": "$per_member"},
            {"$match": {"$expr": {"$lt": ["$per_member.rate", "$overall.avg"]}}},
            {"$project": {"name": "$per_member._id", "marked": "$per_member.marked",
                          "rate_pct": {"$round": ["$per_member.rate", 1]},
                          "gym_average_pct": {"$round": ["$overall.avg", 1]}}},
            {"$project": {"_id": 0}},
            {"$sort": {"rate_pct": 1, "name": 1}},
            {"$limit": 8},
        ],
    },
    {
        "id": "Q11", "category": "Subquery (correlated)",
        "title": "Members with more than one unpaid bill",
        "sql": "SELECT m.member_id, m.name,\n"
               "       (SELECT COUNT(*) FROM payments p\n"
               "        WHERE p.member_id = m.member_pk AND p.status IN ('pending','overdue')) AS unpaid\n"
               "FROM members m\n"
               "WHERE (SELECT COUNT(*) FROM payments p\n"
               "       WHERE p.member_id = m.member_pk AND p.status IN ('pending','overdue')) > 1\n"
               "ORDER BY m.member_id;",
        "collection": "members", "op": "aggregate",
        "pipeline": [
            {"$lookup": {"from": "payments", "let": {"mid": "$_id"}, "as": "unpaid",
                         "pipeline": [{"$match": {"$expr": {"$and": [
                             {"$eq": ["$member_id", "$$mid"]},
                             {"$in": ["$status", UNPAID]}]}}}]}},
            {"$match": {"$expr": {"$gt": [{"$size": "$unpaid"}, 1]}}},
            {"$project": {"_id": 0, "member_id": 1, "name": 1, "tier": "$membership.type",
                          "unpaid_bills": {"$size": "$unpaid"},
                          "amount_due": {"$sum": "$unpaid.amount"}}},
            {"$sort": {"member_id": 1}},
        ],
        "count": True,
    },
    {
        "id": "Q12", "category": "Subquery (EXISTS)",
        "title": "Classes taught by trainers who coach more than 8 members",
        "sql": "SELECT c.class_name, c.trainer_name FROM classes c\n"
               "WHERE EXISTS (SELECT 1 FROM members m\n"
               "              WHERE m.assigned_trainer_id = c.trainer_id\n"
               "              GROUP BY m.assigned_trainer_id HAVING COUNT(*) > 8);",
        "collection": "classes", "op": "aggregate",
        "pipeline": [
            {"$lookup": {"from": "members", "localField": "trainer_id",
                         "foreignField": "assigned_trainer_id", "as": "m"}},
            {"$match": {"$expr": {"$gt": [{"$size": "$m"}, 8]}}},
            {"$project": {"_id": 0, "class_name": 1, "trainer_name": 1, "trainer_members": {"$size": "$m"}}},
            {"$sort": {"class_name": 1}},
        ],
    },
    # ------------------------------------------------------------------ SET OPERATIONS
    {
        "id": "Q13", "category": "Set operation (UNION)",
        "title": "Members enrolled in Morning Yoga or Evening Yoga (each counted once)",
        "sql": "SELECT member_name FROM enrollments WHERE class_name = 'Morning Yoga'\n"
               "UNION\n"
               "SELECT member_name FROM enrollments WHERE class_name = 'Evening Yoga';",
        "collection": "classes", "op": "aggregate",
        "pipeline": [
            {"$facet": {
                "a": [{"$match": {"class_name": "Morning Yoga"}}, {"$project": {"n": "$enrolled_members.member_name"}}],
                "b": [{"$match": {"class_name": "Evening Yoga"}}, {"$project": {"n": "$enrolled_members.member_name"}}],
            }},
            {"$project": {"morning": {"$size": {"$arrayElemAt": ["$a.n", 0]}},
                          "evening": {"$size": {"$arrayElemAt": ["$b.n", 0]}},
                          "result": {"$setUnion": [{"$arrayElemAt": ["$a.n", 0]}, {"$arrayElemAt": ["$b.n", 0]}]}}},
            {"$project": {"morning_yoga": "$morning", "evening_yoga": "$evening",
                          "union_size": {"$size": "$result"}, "result": 1}},
        ],
        "set_result": True,
    },
    {
        "id": "Q14", "category": "Set operation (INTERSECT)",
        "title": "Members enrolled in both CrossFit Burn and Strength 101",
        "sql": "SELECT member_name FROM enrollments WHERE class_name = 'CrossFit Burn'\n"
               "INTERSECT\n"
               "SELECT member_name FROM enrollments WHERE class_name = 'Strength 101';",
        "collection": "classes", "op": "aggregate",
        "pipeline": [
            {"$facet": {
                "a": [{"$match": {"class_name": "CrossFit Burn"}}, {"$project": {"n": "$enrolled_members.member_name"}}],
                "b": [{"$match": {"class_name": "Strength 101"}}, {"$project": {"n": "$enrolled_members.member_name"}}],
            }},
            {"$project": {"result": {"$setIntersection": [{"$arrayElemAt": ["$a.n", 0]},
                                                          {"$arrayElemAt": ["$b.n", 0]}]}}},
            {"$project": {"intersect_size": {"$size": "$result"}, "result": 1}},
        ],
        "set_result": True,
    },
    {
        "id": "Q15", "category": "Set operation (EXCEPT)",
        "title": "Active members who are not enrolled in any class",
        "sql": "SELECT name FROM members WHERE status = 'active'\n"
               "EXCEPT\n"
               "SELECT member_name FROM enrollments;",
        "collection": "members", "op": "aggregate",
        "pipeline": [
            {"$facet": {
                "active": [{"$match": {"membership.status": "active"}},
                           {"$group": {"_id": None, "n": {"$addToSet": "$name"}}}],
                "enrolled": [{"$lookup": {"from": "classes", "localField": "_id",
                                          "foreignField": "enrolled_members.member_id", "as": "c"}},
                             {"$match": {"$expr": {"$gt": [{"$size": "$c"}, 0]}}},
                             {"$group": {"_id": None, "n": {"$addToSet": "$name"}}}],
            }},
            {"$project": {"result": {"$setDifference": [{"$arrayElemAt": ["$active.n", 0]},
                                                        {"$arrayElemAt": ["$enrolled.n", 0]}]},
                          "active_members": {"$size": {"$arrayElemAt": ["$active.n", 0]}},
                          "enrolled_somewhere": {"$size": {"$arrayElemAt": ["$enrolled.n", 0]}}}},
            {"$project": {"active_members": 1, "enrolled_somewhere": 1,
                          "except_size": {"$size": "$result"}, "result": 1}},
        ],
        "set_result": True,
    },
]


# ---------------------------------------------------------------------- execution
def run_query(db, q):
    coll = db[q["collection"]]
    if q["op"] == "find":
        cur = coll.find(q["filter"], q.get("projection"))
        if q.get("sort"):
            cur = cur.sort(q["sort"])
        if q.get("limit"):
            cur = cur.limit(q["limit"])
        rows = list(cur)
        total = coll.count_documents(q["filter"]) if q.get("count") else len(rows)
    else:
        rows = list(coll.aggregate(q["pipeline"]))
        total = len(rows)
    for r in rows:
        if "result" in r and isinstance(r["result"], list):
            r["result"] = sorted(r["result"])
    return rows, total


def _plain(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_plain(x) for x in v]
    return v


def flatten(row, prefix=""):
    out = {}
    for k, v in row.items():
        if isinstance(v, dict):
            out.update(flatten(v, f"{prefix}{k}."))
        elif isinstance(v, list):
            out[prefix + k] = ", ".join(str(x) for x in v)
        else:
            out[prefix + k] = v
    return out


def print_table(rows):
    if not rows:
        print("(no rows)")
        return
    rows = [flatten(_plain(r)) for r in rows]
    cols = list(dict.fromkeys(c for r in rows for c in r))
    w = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("  ".join(c.ljust(w[c]) for c in cols))
    print("  ".join("-" * w[c] for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(w[c]) for c in cols))


# ---------------------------------------------------------------------- mongosh export
def to_js(v, indent=0):
    pad, nxt = "  " * indent, "  " * (indent + 1)
    if isinstance(v, datetime):
        return f'ISODate("{v.strftime("%Y-%m-%dT%H:%M:%SZ")}")'
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, (list, tuple)):
        one = "[" + ", ".join(to_js(x, indent + 1) for x in v) + "]"
        if "\n" not in one and len(one) + len(pad) <= 96:
            return one
        return "[\n" + ",\n".join(nxt + to_js(x, indent + 1) for x in v) + "\n" + pad + "]"
    if isinstance(v, dict):
        if not v:
            return "{}"
        items = [f"{json.dumps(k) if not k.isidentifier() else k}: {to_js(x, indent + 1)}" for k, x in v.items()]
        one = "{ " + ", ".join(items) + " }"
        if len(one) + len(pad) <= 96 and "\n" not in one:
            return one
        return "{\n" + ",\n".join(nxt + i for i in items) + "\n" + pad + "}"
    raise TypeError(type(v))


def query_js(q):
    c = f"db.{q['collection']}"
    if q["op"] == "find":
        s = f"{c}.find(\n  {to_js(q['filter'], 1)},\n  {to_js(q.get('projection') or {}, 1)}\n)"
        if q.get("sort"):
            s += ".sort(" + to_js(dict(q["sort"])) + ")"
        if q.get("limit"):
            s += f".limit({q['limit']})"
        return s + ".toArray()"
    return f"{c}.aggregate({to_js(q['pipeline'])}).toArray()"


def export_js():
    head = ("// Generated by queries.py --export-js. Run after the database has been created and seeded:\n"
            "//   python demo.py --section setup\n")
    lines = [head + "//   mongosh \"mongodb://localhost:27017/?directConnection=true\" mongosh/queries.js\n",
             'db = db.getSiblingDB("gym_db");\n']
    for q in QUERIES:
        lines.append(f"// {q['id']}  {q['category']}: {q['title']}")
        lines.append("// SQL equivalent:\n" + "\n".join("//   " + l for l in q["sql"].splitlines()))
        lines.append(f'print("\\n--- {q["id"]} {q["title"]}");')
        lines.append(f"printjson({query_js(q)});\n")
    with open("mongosh/queries.js", "w") as f:
        f.write("\n".join(lines))

    ddl = ["// Generated by queries.py --export-js. Creates EMPTY collections (drops existing ones), then indexes.\n"
           "// Load data afterwards with mongoimport (data/*.json) or use python demo.py, which does all of this.\n"
           "//   mongosh \"mongodb://localhost:27017/?directConnection=true\" mongosh/ddl.js\n",
           "// Data definition for gym_db: 7 collections with $jsonSchema validators, then 19 indexes.",
           'db = db.getSiblingDB("gym_db");\n']
    for name, schema in VALIDATORS.items():
        ddl.append(f"db.getCollection({json.dumps(name)}).drop();")
        ddl.append(f"db.createCollection({json.dumps(name)}, {{\n  validator: {{ $jsonSchema: "
                   f"{to_js(schema, 2)} }},\n  validationLevel: \"strict\",\n  validationAction: \"error\"\n}});\n")
    for coll, specs in INDEXES.items():
        for keys, opts in specs:
            k = "{ " + ", ".join(f"{json.dumps(f) if not f.replace('_', 'a').isalnum() else f}: "
                                 f"{json.dumps(d)}" for f, d in keys) + " }"
            ddl.append(f"db.{coll}.createIndex({k}, {to_js(opts)});")
    from gym_db.aggregations import MEMBER_DASHBOARD_PIPELINE
    ddl.append("\n// Read-only view used by the member dashboard (hides password_hash).")
    ddl.append('db.getCollection("member_dashboard").drop();')
    ddl.append(f'db.createView("member_dashboard", "members", {to_js(MEMBER_DASHBOARD_PIPELINE)});')
    ddl.append('\nprint("gym_db created: " + db.getCollectionNames().sort().join(", "));')
    with open("mongosh/ddl.js", "w") as f:
        f.write("\n".join(ddl) + "\n")
    print("wrote mongosh/queries.js and mongosh/ddl.js")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="use in-memory mongomock instead of a server")
    ap.add_argument("--only", help="run a single query, e.g. Q11")
    ap.add_argument("--export-js", action="store_true", help="write mongosh/ddl.js and mongosh/queries.js")
    ap.add_argument("--json", help="also save every result to this JSON file")
    args = ap.parse_args()
    if args.export_js:
        export_js()
        return
    db = get_db(mock=args.mock)
    create_collections(db)
    seed(db)
    create_indexes(db)
    print(f"Connected to {'mongomock (in-memory)' if is_mock() else 'MongoDB'}; database '{db.name}' "
          f"recreated and seeded; reference date {REFERENCE_DATE.date()}")
    saved = {}
    for q in QUERIES:
        if args.only and q["id"] != args.only:
            continue
        print("\n" + "=" * 78 + f"\n{q['id']}  [{q['category']}]  {q['title']}\n" + "=" * 78)
        try:
            rows, total = run_query(db, q)
        except NotImplementedError:
            print("(this operator is not available in mongomock; run against a real MongoDB server)")
            continue
        if q.get("set_result"):
            r = _plain(rows[0])
            print("  ".join(f"{k}: {v}" for k, v in r.items() if k != "result"))
            print("result:", ", ".join(r["result"]))
        else:
            print_table(rows)
            print(f"({total} matching document{'s' if total != 1 else ''}"
                  f"{', first ' + str(len(rows)) + ' shown' if total > len(rows) else ''})")
        saved[q["id"]] = {"rows": _plain(rows), "total": total}
    if args.json:
        with open(args.json, "w") as f:
            json.dump(saved, f, indent=1, default=str)


if __name__ == "__main__":
    main()

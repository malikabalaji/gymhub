"""Step 5: advanced NoSQL features, aggregation framework (FR7).

Each function returns the pipeline result. Stages used across the set:
$match $group $project $addFields $lookup $unwind $sort $limit $facet $bucket
$graphLookup $cond $size $round $dateToString $filter $sum $avg $push $first
"""
from .config import REFERENCE_DATE, is_mock


# A1. Monthly revenue trend, split by membership tier ($lookup + $group + $dateToString)
def revenue_trend(db):
    return list(db.payments.aggregate([
        {"$match": {"status": "paid"}},
        {"$lookup": {"from": "members", "localField": "member_id", "foreignField": "_id", "as": "m"}},
        {"$unwind": "$m"},
        {"$group": {
            "_id": {"month": {"$dateToString": {"format": "%Y-%m", "date": "$billing_period_start"}},
                    "tier": "$m.membership.type"},
            "revenue": {"$sum": "$amount"}, "payments": {"$sum": 1}}},
        {"$group": {"_id": "$_id.month",
                    "total_revenue": {"$sum": "$revenue"},
                    "payments": {"$sum": "$payments"},
                    "by_tier": {"$push": {"tier": "$_id.tier", "revenue": "$revenue"}}}},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "month": "$_id", "total_revenue": 1, "payments": 1, "by_tier": 1}},
    ]))


# A2. Class popularity: attendance rate, average turnout and fill rate per class
def class_popularity(db):
    return list(db.attendance.aggregate([
        {"$group": {"_id": "$class_id",
                    "marked": {"$sum": 1},
                    "attended": {"$sum": {"$cond": [{"$in": ["$status", ["present", "late"]]}, 1, 0]}},
                    "sessions": {"$addToSet": "$session_id"}}},
        {"$lookup": {"from": "classes", "localField": "_id", "foreignField": "_id", "as": "c"}},
        {"$unwind": "$c"},
        {"$project": {
            "_id": 0, "class_name": "$c.class_name", "trainer": "$c.trainer_name",
            "enrolled": {"$size": "$c.enrolled_members"}, "capacity": "$c.capacity",
            "sessions_held": {"$size": "$sessions"},
            "avg_turnout": {"$round": [{"$divide": ["$attended", {"$size": "$sessions"}]}, 1]},
            "attendance_rate_pct": {"$round": [{"$multiply": [{"$divide": ["$attended", "$marked"]}, 100]}, 1]},
            "fill_rate_pct": {"$round": [{"$multiply": [
                {"$divide": [{"$size": "$c.enrolled_members"}, "$c.capacity"]}, 100]}, 1]}}},
        {"$sort": {"avg_turnout": -1}},
    ]))


# A3. Members at risk of churning: attendance below 60 percent
def at_risk_members(db, threshold=60):
    return list(db.attendance.aggregate([
        {"$group": {"_id": "$member_id", "name": {"$first": "$member_name"},
                    "total": {"$sum": 1},
                    "attended": {"$sum": {"$cond": [{"$eq": ["$status", "absent"]}, 0, 1]}}}},
        {"$addFields": {"rate_pct": {"$round": [{"$multiply": [{"$divide": ["$attended", "$total"]}, 100]}, 1]}}},
        {"$match": {"rate_pct": {"$lt": threshold}, "total": {"$gte": 4}}},
        {"$lookup": {"from": "members", "localField": "_id", "foreignField": "_id", "as": "m"}},
        {"$unwind": "$m"},
        {"$project": {"_id": 0, "member_id": "$m.member_id", "name": 1, "tier": "$m.membership.type",
                      "sessions_marked": "$total", "attended": 1, "rate_pct": 1}},
        {"$sort": {"rate_pct": 1}},
    ]))


# A4. Outstanding dues with days overdue and contact details (FR6)
def outstanding_dues(db, today=REFERENCE_DATE):
    return list(db.payments.aggregate([
        {"$match": {"status": {"$in": ["pending", "overdue"]}}},
        {"$addFields": {"days_overdue": {"$max": [0, {"$floor": {
            "$divide": [{"$subtract": [today, "$due_date"]}, 86400000]}}]}}},
        {"$group": {"_id": "$member_id", "name": {"$first": "$member_name"},
                    "bills": {"$sum": 1}, "amount_due": {"$sum": "$amount"},
                    "max_days_overdue": {"$max": "$days_overdue"},
                    "statuses": {"$addToSet": "$status"}}},
        {"$lookup": {"from": "members", "localField": "_id", "foreignField": "_id", "as": "m"}},
        {"$unwind": "$m"},
        {"$project": {"_id": 0, "member_id": "$m.member_id", "name": 1, "phone": "$m.phone",
                      "tier": "$m.membership.type", "bills": 1, "amount_due": 1, "max_days_overdue": 1,
                      "priority": {"$cond": [{"$gte": ["$max_days_overdue", 15]}, "HIGH",
                                             {"$cond": [{"$gt": ["$max_days_overdue", 0]}, "MEDIUM", "LOW"]}]}}},
        {"$sort": {"max_days_overdue": -1, "amount_due": -1}},
    ]))


# A5. Trainer workload: members, active plans, classes (three $lookup joins)
def trainer_workload(db):
    return list(db.trainers.aggregate([
        {"$lookup": {"from": "members", "localField": "_id", "foreignField": "assigned_trainer_id", "as": "mem"}},
        {"$lookup": {"from": "workout_plans", "localField": "_id", "foreignField": "trainer_id", "as": "plans"}},
        {"$lookup": {"from": "classes", "localField": "_id", "foreignField": "trainer_id", "as": "cls"}},
        {"$project": {"_id": 0, "trainer_id": 1, "name": 1, "specialization": 1,
                      "members": {"$size": "$mem"},
                      "active_plans": {"$size": {"$filter": {"input": "$plans", "as": "p",
                                                             "cond": {"$eq": ["$$p.status", "active"]}}}},
                      "classes": {"$size": "$cls"},
                      "class_names": "$cls.class_name"}},
        {"$sort": {"members": -1}},
    ]))


# A6. Membership dashboard in ONE query: $facet runs three sub-pipelines, $bucket groups ages
def membership_overview(db, today=REFERENCE_DATE):
    res = list(db.members.aggregate([
        {"$addFields": {"age": {"$floor": {"$divide": [{"$subtract": [today, "$dob"]}, 31557600000]}}}},
        {"$facet": {
            "by_tier": [{"$group": {"_id": "$membership.type", "count": {"$sum": 1}}}, {"$sort": {"_id": 1}}],
            "by_status": [{"$group": {"_id": "$membership.status", "count": {"$sum": 1}}}, {"$sort": {"_id": 1}}],
            "age_groups": [{"$bucket": {"groupBy": "$age", "boundaries": [18, 25, 35, 45, 60],
                                        "default": "60+", "output": {"count": {"$sum": 1}}}}],
            "by_city": [{"$group": {"_id": "$address.city", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}],
        }},
    ]))
    return res[0]


# A7. Most prescribed exercises across all active plans ($unwind on embedded array)
def top_exercises(db, limit=8):
    return list(db.workout_plans.aggregate([
        {"$match": {"status": "active"}},
        {"$unwind": "$exercises"},
        {"$group": {"_id": "$exercises.exercise_name", "plans": {"$sum": 1},
                    "avg_sets": {"$avg": "$exercises.sets"}, "avg_weight_kg": {"$avg": "$exercises.weight_kg"}}},
        {"$project": {"_id": 0, "exercise": "$_id", "plans": 1,
                      "avg_sets": {"$round": ["$avg_sets", 1]}, "avg_weight_kg": {"$round": ["$avg_weight_kg", 1]}}},
        {"$sort": {"plans": -1, "exercise": 1}},
        {"$limit": limit},
    ]))


# A8. Peak check-in hours (string operators on check_in_time)
def peak_hours(db):
    return list(db.attendance.aggregate([
        {"$match": {"status": {"$ne": "absent"}}},
        {"$group": {"_id": {"$substr": ["$check_in_time", 0, 2]}, "check_ins": {"$sum": 1}}},
        {"$project": {"_id": 0, "hour": {"$concat": ["$_id", ":00"]}, "check_ins": 1}},
        {"$sort": {"check_ins": -1}},
    ]))


# G1. Graph traversal: full referral network of a member ($graphLookup, recursive)
def referral_network(db, member_id):
    res = list(db.members.aggregate([
        {"$match": {"member_id": member_id}},
        {"$graphLookup": {"from": "members", "startWith": "$_id", "connectFromField": "_id",
                          "connectToField": "referred_by", "as": "network",
                          "maxDepth": 5, "depthField": "level"}},
        {"$project": {"_id": 0, "member_id": 1, "name": 1,
                      "network": {"$map": {"input": "$network", "as": "n",
                                           "in": {"member_id": "$$n.member_id", "name": "$$n.name",
                                                  "level": {"$add": ["$$n.level", 1]}}}}}},
    ]))
    if res:
        res[0]["network"].sort(key=lambda n: (n["level"], n["member_id"]))
        res[0]["network_size"] = len(res[0]["network"])
    return res[0] if res else None


# G2. Top referrers: who brought in the largest downstream network
def top_referrers(db, limit=5):
    return list(db.members.aggregate([
        {"$match": {"referred_by": None}},
        {"$graphLookup": {"from": "members", "startWith": "$_id", "connectFromField": "_id",
                          "connectToField": "referred_by", "as": "network", "depthField": "level"}},
        {"$project": {"_id": 0, "member_id": 1, "name": 1, "network_size": {"$size": "$network"},
                      "direct": {"$size": {"$filter": {"input": "$network", "as": "n",
                                                       "cond": {"$eq": ["$$n.level", 0]}}}},
                      "levels": {"$add": [{"$max": "$network.level"}, 1]}}},
        {"$match": {"network_size": {"$gt": 0}}},
        {"$sort": {"network_size": -1, "member_id": 1}},
        {"$limit": limit},
    ]))


# V1. Read-only view powering the member dashboard (FR3); hides password_hash
MEMBER_DASHBOARD_PIPELINE = [
    {"$lookup": {"from": "trainers", "localField": "assigned_trainer_id", "foreignField": "_id", "as": "t"}},
    {"$lookup": {"from": "payments", "localField": "_id", "foreignField": "member_id", "as": "p"}},
    {"$project": {"_id": 0, "member_id": 1, "name": 1, "tier": "$membership.type",
                  "status": "$membership.status", "trainer": {"$first": "$t.name"},
                  "unpaid_amount": {"$sum": {"$map": {
                      "input": {"$filter": {"input": "$p", "as": "x", "cond": {"$ne": ["$$x.status", "paid"]}}},
                      "as": "u", "in": "$$u.amount"}}}}},
]


def create_views(db):
    if is_mock():
        return False
    db.drop_collection("member_dashboard")
    db.command({"create": "member_dashboard", "viewOn": "members", "pipeline": MEMBER_DASHBOARD_PIPELINE})
    return True


def member_dashboard(db, member_id):
    if is_mock():  # mongomock has no views; run the same pipeline directly
        res = list(db.members.aggregate([{"$match": {"member_id": member_id}}] + MEMBER_DASHBOARD_PIPELINE))
        return res[0] if res else None
    return db.member_dashboard.find_one({"member_id": member_id})

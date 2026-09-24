"""Step 3: indexes (NFR1 performance) and an explain() comparison.

Implements every index promised in Review 1 section 6.8, plus a text index for class
search and a partial index that only covers unpaid dues.
"""
from pymongo import ASCENDING, DESCENDING, TEXT

from .config import is_mock

INDEXES = {
    "members": [
        ([("email", ASCENDING)], {"unique": True, "name": "uq_email"}),
        ([("member_id", ASCENDING)], {"unique": True, "name": "uq_member_id"}),
        ([("assigned_trainer_id", ASCENDING)], {"name": "ix_trainer"}),
        ([("membership.type", ASCENDING), ("membership.status", ASCENDING)], {"name": "ix_tier_status"}),
        ([("referred_by", ASCENDING)], {"name": "ix_referred_by"}),
    ],
    "trainers": [
        ([("email", ASCENDING)], {"unique": True, "name": "uq_email"}),
        ([("trainer_id", ASCENDING)], {"unique": True, "name": "uq_trainer_id"}),
    ],
    "workout_plans": [
        ([("member_id", ASCENDING), ("status", ASCENDING)], {"name": "ix_member_status"}),
        ([("trainer_id", ASCENDING)], {"name": "ix_trainer"}),
    ],
    "classes": [
        ([("trainer_id", ASCENDING)], {"name": "ix_trainer"}),
        ([("enrolled_members.member_id", ASCENDING)], {"name": "ix_enrolled_member"}),  # multikey
        ([("class_name", TEXT), ("category", TEXT)], {"name": "tx_class_search"}),
    ],
    "class_sessions": [
        ([("class_id", ASCENDING), ("date", ASCENDING)], {"name": "ix_class_date"}),
    ],
    "attendance": [
        ([("member_id", ASCENDING), ("date", DESCENDING)], {"name": "ix_member_date"}),
        ([("session_id", ASCENDING), ("member_id", ASCENDING)], {"unique": True, "name": "uq_session_member"}),
        ([("class_id", ASCENDING), ("status", ASCENDING)], {"name": "ix_class_status"}),
    ],
    "payments": [
        ([("member_id", ASCENDING), ("status", ASCENDING)], {"name": "ix_member_status"}),
        ([("due_date", ASCENDING)], {"name": "ix_due_date"}),
        ([("status", ASCENDING), ("due_date", ASCENDING)],
         {"name": "px_unpaid_dues", "partialFilterExpression": {"status": {"$in": ["pending", "overdue"]}}}),
    ],
}


def create_indexes(db):
    created = []
    for coll, specs in INDEXES.items():
        for keys, opts in specs:
            if is_mock() and ("partialFilterExpression" in opts or keys[0][1] == TEXT):
                continue  # mongomock does not support partial or text indexes
            db[coll].create_index(keys, **opts)
            created.append(f"{coll}.{opts['name']}")
    return created


def explain_comparison(db):
    """Run the same query with and without an index and compare the query plans.

    Query: a member's attendance history, newest first (dashboard query).
    """
    if is_mock():
        return None
    member_id = db.members.find_one({"member_id": "MEM1001"})["_id"]
    query = {"member_id": member_id}

    def stats(hint):
        plan = db.attendance.find(query).sort("date", -1).hint(hint).explain()
        es = plan["executionStats"]
        stage = plan["queryPlanner"]["winningPlan"]
        stage = stage.get("queryPlan", stage)  # MongoDB 7+ (slot-based engine) nests the plan
        # walk down to the leaf stage (COLLSCAN or IXSCAN)
        while "inputStage" in stage:
            stage = stage["inputStage"]
        return {"stage": stage["stage"], "docs_examined": es["totalDocsExamined"],
                "keys_examined": es["totalKeysExamined"], "returned": es["nReturned"],
                "time_ms": es["executionTimeMillis"]}

    return {"without_index": stats([("$natural", 1)]), "with_index": stats("ix_member_date")}

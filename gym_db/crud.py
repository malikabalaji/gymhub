"""Step 4: CRUD operations for every collection (FR1 to FR6, FR8).

MongoDB has no foreign keys, so referential integrity is enforced here (NFR5):
  * references are checked before insert/update,
  * denormalized names are propagated when the source changes,
  * deletes either cascade or are blocked when dependent data exists.
"""
from datetime import datetime

import bcrypt
from bson import ObjectId
from pymongo import ReturnDocument

from .config import REFERENCE_DATE, TIER_FEES

SAFE = {"password_hash": 0}  # never return password hashes to callers


class IntegrityError(Exception):
    pass


def _next_code(coll, field, prefix, width):
    last = coll.find_one({field: {"$regex": f"^{prefix}"}}, sort=[(field, -1)], projection={field: 1})
    n = int(last[field][len(prefix):]) + 1 if last else 1
    return f"{prefix}{n:0{width}d}"


def _require(db, coll, _id, label):
    doc = db[coll].find_one({"_id": _id})
    if not doc:
        raise IntegrityError(f"{label} {_id} does not exist")
    return doc


def _member_oid(db, member_id):
    doc = db.members.find_one({"member_id": member_id}, {"_id": 1})
    if not doc:
        raise IntegrityError(f"Member {member_id} not found")
    return doc["_id"]


# ------------------------------------------------------------------ MEMBERS
def create_member(db, name, email, phone, dob, gender, password, tier="Basic",
                  trainer_id=None, referred_by=None, city="Vellore", pincode="632014"):
    trainer_oid = None
    if trainer_id:
        trainer_oid = db.trainers.find_one({"trainer_id": trainer_id}, {"_id": 1})
        if not trainer_oid:
            raise IntegrityError(f"Trainer {trainer_id} not found")
        trainer_oid = trainer_oid["_id"]
    ref_oid = _member_oid(db, referred_by) if referred_by else None
    start = REFERENCE_DATE.replace(day=1)
    doc = {
        "member_id": _next_code(db.members, "member_id", "MEM", 4),
        "name": name, "email": email.lower(), "phone": phone, "dob": dob, "gender": gender,
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "role": "member",
        "membership": {"type": tier, "status": "active", "start_date": start,
                       "end_date": datetime(start.year + 1, start.month, 1)},
        "assigned_trainer_id": trainer_oid, "referred_by": ref_oid,
        "address": {"line1": "", "city": city, "pincode": pincode},
        "emergency_contact": {"name": "", "phone": ""},
        "created_at": REFERENCE_DATE,
    }
    db.members.insert_one(doc)
    return doc["member_id"]


def get_member(db, member_id):
    return db.members.find_one({"member_id": member_id}, SAFE)


def list_members(db, tier=None, status=None, city=None, page=1, page_size=10):
    q = {}
    if tier:
        q["membership.type"] = tier
    if status:
        q["membership.status"] = status
    if city:
        q["address.city"] = city
    cur = (db.members.find(q, {"member_id": 1, "name": 1, "membership": 1, "address.city": 1, "_id": 0})
           .sort("member_id", 1).skip((page - 1) * page_size).limit(page_size))
    return list(cur), db.members.count_documents(q)


def update_member(db, member_id, **fields):
    """Update profile fields. A name change is propagated to every denormalized copy."""
    allowed = {"name", "phone", "email", "address", "emergency_contact"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"Cannot update {bad} here")
    doc = db.members.find_one_and_update({"member_id": member_id}, {"$set": fields},
                                         projection=SAFE, return_document=ReturnDocument.AFTER)
    if doc and "name" in fields:
        oid, name = doc["_id"], fields["name"]
        for coll in ("workout_plans", "attendance", "payments"):
            db[coll].update_many({"member_id": oid}, {"$set": {"member_name": name}})
        db.classes.update_many({"enrolled_members.member_id": oid},
                               {"$set": {"enrolled_members.$.member_name": name}})  # positional $
    return doc


def change_membership(db, member_id, tier=None, status=None):
    s = {}
    if tier:
        if tier not in TIER_FEES:
            raise ValueError("tier must be Basic, Premium or VIP")
        s["membership.type"] = tier
    if status:
        s["membership.status"] = status
    return db.members.find_one_and_update({"member_id": member_id}, {"$set": s}, projection=SAFE,
                                          return_document=ReturnDocument.AFTER)


def assign_trainer(db, member_id, trainer_id):
    t = db.trainers.find_one({"trainer_id": trainer_id}, {"_id": 1})
    if not t:
        raise IntegrityError(f"Trainer {trainer_id} not found")
    return db.members.update_one({"member_id": member_id},
                                 {"$set": {"assigned_trainer_id": t["_id"]}}).modified_count


def delete_member(db, member_id):
    """Blocked if dues are outstanding; otherwise cascades to plans and class rosters.
    Attendance and payment history are kept as the gym's audit trail."""
    oid = _member_oid(db, member_id)
    dues = db.payments.count_documents({"member_id": oid, "status": {"$in": ["pending", "overdue"]}})
    if dues:
        raise IntegrityError(f"{member_id} has {dues} unpaid bill(s); settle before deleting")
    plans = db.workout_plans.delete_many({"member_id": oid}).deleted_count
    rosters = db.classes.update_many({}, {"$pull": {"enrolled_members": {"member_id": oid}}}).modified_count
    db.members.update_many({"referred_by": oid}, {"$set": {"referred_by": None}})
    db.members.delete_one({"_id": oid})
    return {"plans_deleted": plans, "classes_updated": rosters}


# ------------------------------------------------------------------ TRAINERS
def create_trainer(db, name, email, phone, password, specialization, certification, experience_years):
    doc = {"trainer_id": _next_code(db.trainers, "trainer_id", "TRN", 2), "name": name,
           "email": email.lower(), "phone": phone,
           "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
           "role": "trainer", "specialization": specialization, "certification": certification,
           "experience_years": experience_years, "availability": [], "created_at": REFERENCE_DATE}
    db.trainers.insert_one(doc)
    return doc["trainer_id"]


def get_trainer(db, trainer_id):
    return db.trainers.find_one({"trainer_id": trainer_id}, SAFE)


def find_trainers_by_skill(db, skill):
    return list(db.trainers.find({"specialization": skill}, {"_id": 0, "trainer_id": 1, "name": 1,
                                                            "specialization": 1}))


def add_specialization(db, trainer_id, skill):
    # $addToSet: no duplicates in the embedded array
    return db.trainers.update_one({"trainer_id": trainer_id},
                                  {"$addToSet": {"specialization": skill}}).modified_count


def set_availability(db, trainer_id, day, start_time, end_time):
    db.trainers.update_one({"trainer_id": trainer_id}, {"$pull": {"availability": {"day": day}}})
    return db.trainers.update_one({"trainer_id": trainer_id}, {"$push": {"availability": {
        "day": day, "start_time": start_time, "end_time": end_time}}}).modified_count


def delete_trainer(db, trainer_id):
    t = db.trainers.find_one({"trainer_id": trainer_id}, {"_id": 1})
    if not t:
        raise IntegrityError(f"Trainer {trainer_id} not found")
    members = db.members.count_documents({"assigned_trainer_id": t["_id"]})
    classes = db.classes.count_documents({"trainer_id": t["_id"]})
    if members or classes:
        raise IntegrityError(f"{trainer_id} still has {members} members and {classes} classes; reassign first")
    return db.trainers.delete_one({"_id": t["_id"]}).deleted_count


# ------------------------------------------------------------------ WORKOUT PLANS
def create_workout_plan(db, member_id, goal, duration_weeks, exercises):
    m = db.members.find_one({"member_id": member_id})
    if not m:
        raise IntegrityError(f"Member {member_id} not found")
    t = _require(db, "trainers", m["assigned_trainer_id"], "Trainer")
    # business rule: only one active plan per member
    db.workout_plans.update_many({"member_id": m["_id"], "status": "active"},
                                 {"$set": {"status": "completed", "updated_at": REFERENCE_DATE}})
    doc = {"plan_id": _next_code(db.workout_plans, "plan_id", "WP", 4),
           "member_id": m["_id"], "member_name": m["name"],
           "trainer_id": t["_id"], "trainer_name": t["name"],
           "goal": goal, "duration_weeks": duration_weeks, "status": "active",
           "exercises": exercises, "created_at": REFERENCE_DATE, "updated_at": REFERENCE_DATE}
    db.workout_plans.insert_one(doc)
    return doc["plan_id"]


def get_active_plan(db, member_id):
    return db.workout_plans.find_one({"member_id": _member_oid(db, member_id), "status": "active"},
                                     {"_id": 0, "member_id": 0, "trainer_id": 0})


def add_exercise(db, plan_id, exercise):
    return db.workout_plans.update_one({"plan_id": plan_id},
                                       {"$push": {"exercises": exercise},
                                        "$set": {"updated_at": REFERENCE_DATE}}).modified_count


def progress_exercise(db, plan_id, exercise_name, add_kg):
    """Progressive overload: increase weight of one embedded exercise (positional $ operator)."""
    return db.workout_plans.update_one(
        {"plan_id": plan_id, "exercises.exercise_name": exercise_name},
        {"$inc": {"exercises.$.weight_kg": add_kg}, "$set": {"updated_at": REFERENCE_DATE}}).modified_count


def remove_exercise(db, plan_id, exercise_name):
    return db.workout_plans.update_one({"plan_id": plan_id},
                                       {"$pull": {"exercises": {"exercise_name": exercise_name}}}).modified_count


def delete_workout_plan(db, plan_id):
    return db.workout_plans.delete_one({"plan_id": plan_id}).deleted_count


# ------------------------------------------------------------------ CLASSES
def create_class(db, class_name, category, trainer_id, capacity, schedule):
    t = db.trainers.find_one({"trainer_id": trainer_id})
    if not t:
        raise IntegrityError(f"Trainer {trainer_id} not found")
    doc = {"class_id": _next_code(db.classes, "class_id", "CLS", 2), "class_name": class_name,
           "category": category, "trainer_id": t["_id"], "trainer_name": t["name"],
           "capacity": capacity, "schedule": schedule, "enrolled_members": []}
    db.classes.insert_one(doc)
    return doc["class_id"]


def get_class(db, class_id):
    return db.classes.find_one({"class_id": class_id}, {"_id": 0, "trainer_id": 0})


def enroll_member(db, class_id, member_id):
    """FR4. Atomic single-document update: the filter itself checks capacity and duplicates,
    so two simultaneous requests can never overbook the class."""
    m = db.members.find_one({"member_id": member_id, "membership.status": "active"})
    if not m:
        raise IntegrityError(f"{member_id} not found or membership not active")
    res = db.classes.update_one(
        {"class_id": class_id,
         "enrolled_members.member_id": {"$ne": m["_id"]},
         "$expr": {"$lt": [{"$size": "$enrolled_members"}, "$capacity"]}},
        {"$push": {"enrolled_members": {"member_id": m["_id"], "member_name": m["name"],
                                        "enrolled_on": REFERENCE_DATE}}})
    if res.modified_count == 0:
        raise IntegrityError(f"Cannot enroll {member_id} in {class_id}: class full or already enrolled")
    return True


def withdraw_member(db, class_id, member_id):
    oid = _member_oid(db, member_id)
    return db.classes.update_one({"class_id": class_id},
                                 {"$pull": {"enrolled_members": {"member_id": oid}}}).modified_count


def member_classes(db, member_id):
    oid = _member_oid(db, member_id)
    return list(db.classes.find({"enrolled_members.member_id": oid},
                                {"_id": 0, "class_id": 1, "class_name": 1, "schedule": 1, "trainer_name": 1}))


def delete_class(db, class_id):
    c = db.classes.find_one({"class_id": class_id}, {"_id": 1})
    if not c:
        raise IntegrityError(f"Class {class_id} not found")
    future = db.class_sessions.delete_many({"class_id": c["_id"], "status": "scheduled"}).deleted_count
    db.classes.delete_one({"_id": c["_id"]})
    return {"future_sessions_removed": future}


# ------------------------------------------------------------------ SESSIONS & ATTENDANCE
def create_session(db, class_id, date, start_time, end_time):
    c = db.classes.find_one({"class_id": class_id})
    if not c:
        raise IntegrityError(f"Class {class_id} not found")
    doc = {"session_id": _next_code(db.class_sessions, "session_id", "SES", 4), "class_id": c["_id"],
           "class_name": c["class_name"], "trainer_id": c["trainer_id"], "date": date,
           "start_time": start_time, "end_time": end_time, "status": "scheduled"}
    db.class_sessions.insert_one(doc)
    return doc["session_id"]


def cancel_session(db, session_id):
    return db.class_sessions.update_one({"session_id": session_id, "status": "scheduled"},
                                        {"$set": {"status": "cancelled"}}).modified_count


def mark_attendance(db, session_id, member_id, status, check_in_time=None):
    """FR5. Upsert keyed on (session, member): re-marking corrects the record, never duplicates it."""
    s = db.class_sessions.find_one({"session_id": session_id})
    if not s:
        raise IntegrityError(f"Session {session_id} not found")
    m = db.members.find_one({"member_id": member_id})
    if not m:
        raise IntegrityError(f"Member {member_id} not found")
    return db.attendance.update_one(
        {"session_id": s["_id"], "member_id": m["_id"]},
        {"$set": {"status": status, "check_in_time": check_in_time},
         "$setOnInsert": {"class_id": s["class_id"], "member_name": m["name"], "date": s["date"]}},
        upsert=True)


def attendance_history(db, member_id, limit=5):
    oid = _member_oid(db, member_id)
    return list(db.attendance.find({"member_id": oid}, {"_id": 0, "date": 1, "status": 1,
                                                        "check_in_time": 1, "class_id": 1})
                .sort("date", -1).limit(limit))


def delete_attendance(db, session_id, member_id):
    s = db.class_sessions.find_one({"session_id": session_id}, {"_id": 1})
    return db.attendance.delete_one({"session_id": s["_id"], "member_id": _member_oid(db, member_id)}).deleted_count


# ------------------------------------------------------------------ PAYMENTS
def create_invoice(db, member_id, period_start, period_end, due_date):
    m = db.members.find_one({"member_id": member_id})
    if not m:
        raise IntegrityError(f"Member {member_id} not found")
    doc = {"payment_id": _next_code(db.payments, "payment_id", "PAY", 4), "member_id": m["_id"],
           "member_name": m["name"], "amount": TIER_FEES[m["membership"]["type"]], "currency": "INR",
           "payment_mode": None, "status": "pending", "billing_period_start": period_start,
           "billing_period_end": period_end, "payment_date": None, "due_date": due_date}
    db.payments.insert_one(doc)
    return doc["payment_id"]


def record_payment(db, payment_id, mode, paid_on=None):
    res = db.payments.update_one(
        {"payment_id": payment_id, "status": {"$in": ["pending", "overdue"]}},  # paid bills are immutable
        {"$set": {"status": "paid", "payment_mode": mode, "payment_date": paid_on or REFERENCE_DATE}})
    if not res.modified_count:
        return None
    return db.payments.find_one({"payment_id": payment_id},
                                {"_id": 0, "payment_id": 1, "status": 1, "amount": 1, "payment_mode": 1})


def flag_overdue(db, today=REFERENCE_DATE):
    """FR6. Nightly sweep: any pending bill past its due date becomes overdue (uses ix_due_date)."""
    return db.payments.update_many({"status": "pending", "due_date": {"$lt": today}},
                                   {"$set": {"status": "overdue"}}).modified_count


def member_dues(db, member_id):
    oid = _member_oid(db, member_id)
    return list(db.payments.find({"member_id": oid, "status": {"$ne": "paid"}},
                                 {"_id": 0, "payment_id": 1, "amount": 1, "status": 1, "due_date": 1}))


def delete_payment(db, payment_id):
    # only unpaid invoices raised in error may be deleted; paid records are immutable
    return db.payments.delete_one({"payment_id": payment_id, "status": "pending"}).deleted_count


# ------------------------------------------------------------------ AUTH (FR8)
def authenticate(db, email, password):
    for coll in ("members", "trainers"):
        u = db[coll].find_one({"email": email.lower()})
        if u and bcrypt.checkpw(password.encode(), u["password_hash"].encode()):
            return {"role": u["role"], "id": u.get("member_id") or u.get("trainer_id"), "name": u["name"]}
    return None

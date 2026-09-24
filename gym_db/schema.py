"""Step 1: create the seven collections with $jsonSchema validators.

MongoDB is schema-flexible, but validators give us database-level guarantees on
required fields, data types and allowed enum values (FR1, NFR5).
"""
from .config import COLLECTIONS, is_mock

OID = "objectId"

VALIDATORS = {
    "members": {
        "bsonType": "object",
        "required": ["member_id", "name", "email", "password_hash", "role", "membership"],
        "properties": {
            "member_id": {"bsonType": "string", "pattern": "^MEM[0-9]{4}$"},
            "name": {"bsonType": "string", "minLength": 2},
            "email": {"bsonType": "string", "pattern": "^.+@.+\\..+$"},
            "phone": {"bsonType": "string", "pattern": "^[0-9]{10}$"},
            "gender": {"enum": ["Male", "Female", "Other"]},
            "role": {"enum": ["member"]},
            "membership": {
                "bsonType": "object",
                "required": ["type", "status", "start_date", "end_date"],
                "properties": {
                    "type": {"enum": ["Basic", "Premium", "VIP"]},
                    "status": {"enum": ["active", "expired", "frozen"]},
                    "start_date": {"bsonType": "date"},
                    "end_date": {"bsonType": "date"},
                },
            },
            "assigned_trainer_id": {"bsonType": [OID, "null"]},
            "referred_by": {"bsonType": [OID, "null"]},
        },
    },
    "trainers": {
        "bsonType": "object",
        "required": ["trainer_id", "name", "email", "password_hash", "role"],
        "properties": {
            "trainer_id": {"bsonType": "string", "pattern": "^TRN[0-9]{2}$"},
            "role": {"enum": ["trainer"]},
            "specialization": {"bsonType": "array", "items": {"bsonType": "string"}},
            "experience_years": {"bsonType": ["int", "long", "double"], "minimum": 0},
            "availability": {
                "bsonType": "array",
                "items": {"bsonType": "object", "required": ["day", "start_time", "end_time"]},
            },
        },
    },
    "workout_plans": {
        "bsonType": "object",
        "required": ["plan_id", "member_id", "trainer_id", "goal", "status", "exercises"],
        "properties": {
            "member_id": {"bsonType": OID},
            "trainer_id": {"bsonType": OID},
            "duration_weeks": {"bsonType": ["int", "long"], "minimum": 1, "maximum": 52},
            "status": {"enum": ["active", "completed"]},
            "exercises": {
                "bsonType": "array",
                "minItems": 1,
                "items": {
                    "bsonType": "object",
                    "required": ["day", "exercise_name", "sets", "reps"],
                    "properties": {
                        "sets": {"bsonType": ["int", "long"], "minimum": 1},
                        "reps": {"bsonType": ["int", "long"], "minimum": 1},
                    },
                },
            },
        },
    },
    "classes": {
        "bsonType": "object",
        "required": ["class_id", "class_name", "category", "trainer_id", "capacity"],
        "properties": {
            "trainer_id": {"bsonType": OID},
            "capacity": {"bsonType": ["int", "long"], "minimum": 1, "maximum": 50},
            "schedule": {"bsonType": "array"},
            "enrolled_members": {"bsonType": "array"},
        },
    },
    "class_sessions": {
        "bsonType": "object",
        "required": ["session_id", "class_id", "date", "status"],
        "properties": {
            "class_id": {"bsonType": OID},
            "date": {"bsonType": "date"},
            "status": {"enum": ["scheduled", "completed", "cancelled"]},
        },
    },
    "attendance": {
        "bsonType": "object",
        "required": ["session_id", "class_id", "member_id", "date", "status"],
        "properties": {
            "session_id": {"bsonType": OID},
            "member_id": {"bsonType": OID},
            "status": {"enum": ["present", "absent", "late"]},
        },
    },
    "payments": {
        "bsonType": "object",
        "required": ["payment_id", "member_id", "amount", "status", "due_date"],
        "properties": {
            "member_id": {"bsonType": OID},
            "amount": {"bsonType": ["int", "long", "double"], "minimum": 0},
            "currency": {"enum": ["INR"]},
            "payment_mode": {"enum": ["cash", "card", "UPI", None]},
            "status": {"enum": ["paid", "pending", "overdue"]},
            "due_date": {"bsonType": "date"},
        },
    },
}


def create_collections(db, drop_existing: bool = True):
    """Drop (optionally) and create every collection with its validator."""
    for name in COLLECTIONS:
        if drop_existing:
            db.drop_collection(name)
        if is_mock():
            # mongomock does not implement validators; create a plain collection.
            db.create_collection(name)
        else:
            db.create_collection(
                name,
                validator={"$jsonSchema": VALIDATORS[name]},
                validationLevel="strict",
                validationAction="error",
            )
    return COLLECTIONS

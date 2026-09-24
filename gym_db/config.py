"""Connection and shared settings for the Gym Membership Management System."""
import os
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/?directConnection=true")
DB_NAME = os.getenv("GYM_DB_NAME", "gym_db")

# Fixed "today" so the seeded data and every report are reproducible during the demo.
REFERENCE_DATE = datetime(2026, 9, 24)

# Monthly membership fee per tier (INR)
TIER_FEES = {"Basic": 1500, "Premium": 2500, "VIP": 4000}

COLLECTIONS = ["members", "trainers", "workout_plans", "classes",
               "class_sessions", "attendance", "payments"]

_client = None
IS_MOCK = False


def get_client(mock: bool = False):
    """Return a MongoClient. mock=True uses mongomock (in-memory) for offline testing."""
    global _client, IS_MOCK
    if _client is None:
        if mock:
            import mongomock
            from . import mockpatch  # noqa: F401  ($round support for offline tests)
            _client = mongomock.MongoClient()
            IS_MOCK = True
        else:
            from pymongo import MongoClient
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            _client.admin.command("ping")
    return _client


def get_db(mock: bool = False):
    return get_client(mock)[DB_NAME]


def is_mock() -> bool:
    return IS_MOCK


def supports_transactions(db) -> bool:
    """Transactions need a replica set or sharded cluster (Atlas, or mongod --replSet)."""
    if IS_MOCK:
        return False
    hello = db.client.admin.command("hello")
    return "setName" in hello or hello.get("msg") == "isdbgrid"

"""Database connection and initialization helpers for the API layer."""
import os
import bcrypt
from gym_db import config as gym_config


def ensure_admin(db):
    """Safely ensure the admins collection exists with indexes and default admin.
    
    CRITICAL: Never drops or touches existing collections or documents.
    """
    existing = db.list_collection_names()
    if "admins" not in existing:
        db.create_collection("admins")
        try:
            db.admins.create_index([("email", 1)], unique=True)
            db.admins.create_index([("admin_id", 1)], unique=True)
        except Exception:
            pass

    admin = db.admins.find_one({"email": "admin@gym.com"})
    if not admin:
        rounds = 4 if gym_config.is_mock() else 10
        pw_hash = bcrypt.hashpw(b"Admin@123", bcrypt.gensalt(rounds=rounds)).decode("utf-8")
        db.admins.insert_one({
            "admin_id": "ADM01",
            "name": "Gym Administrator",
            "email": "admin@gym.com",
            "phone": "9876543210",
            "password_hash": pw_hash,
            "role": "admin",
            "created_at": gym_config.REFERENCE_DATE,
        })


def get_database(mock: bool = None):
    """Return the database handle and ensure admin identity exists safely.
    
    If live MongoDB is not reachable or USE_MOCK is set, gracefully falls back
    to in-memory mock database initialized with reproducible sample data.
    """
    if mock is None:
        use_mock_env = os.getenv("USE_MOCK", "").lower() in ("true", "1", "yes")
        if use_mock_env:
            mock = True
        else:
            try:
                db = gym_config.get_db(mock=False)
                ensure_admin(db)
                return db
            except Exception as e:
                # Live server ping failed; fall back to in-memory mock
                mock = True

    # In mock mode, initialize collections, sample data, and admin if not yet seeded
    gym_config._client = None
    db = gym_config.get_db(mock=True)
    if "members" not in db.list_collection_names() or db.members.count_documents({}) == 0:
        from gym_db.schema import create_collections
        from gym_db.seed import seed
        from gym_db.indexes import create_indexes
        create_collections(db)
        seed(db)
        create_indexes(db)
    ensure_admin(db)
    return db


def get_db():
    """FastAPI dependency to yield the configured database."""
    return get_database()

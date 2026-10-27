"""Live-branch initialization logic exercised only against mongomock databases."""
import pytest
import mongomock

import api.database as api_database
from gym_db import config as gym_config
from gym_db import seed as seed_module


@pytest.fixture
def isolated_live_branch(monkeypatch):
    """Route get_database's live branch to an isolated in-memory database."""
    client = mongomock.MongoClient()
    db = client["gymhub_live_init_test"]
    monkeypatch.setenv("USE_MOCK", "false")
    monkeypatch.setattr(gym_config, "_client", None)
    monkeypatch.setattr(gym_config, "IS_MOCK", False)
    monkeypatch.setattr(gym_config, "get_db", lambda mock=False: db)

    # Mongomock does not enforce server validators or every index type.
    import gym_db.schema as schema
    import gym_db.indexes as indexes
    monkeypatch.setattr(schema, "is_mock", lambda: True)
    monkeypatch.setattr(indexes, "is_mock", lambda: True)
    rng_state = seed_module.rng.getstate()
    yield db
    seed_module.rng.setstate(rng_state)


def test_empty_live_database_initializes_original_collections(isolated_live_branch):
    db = isolated_live_branch
    result = api_database.get_database()

    assert result is db
    assert set(gym_config.COLLECTIONS).issubset(db.list_collection_names())
    assert all(db[name].count_documents({}) > 0 for name in gym_config.COLLECTIONS)
    assert db.admins.find_one({"email": "admin@gym.com"})


def test_existing_original_collection_skips_seeding(isolated_live_branch, monkeypatch):
    db = isolated_live_branch
    db.members.insert_one({"member_id": "MEM9001", "marker": "keep"})
    monkeypatch.setattr(seed_module, "seed", lambda database: pytest.fail("seed must not run when an original collection exists"))

    result = api_database.get_database()

    assert result is db
    assert db.members.find_one({"member_id": "MEM9001"})["marker"] == "keep"
    assert not (set(gym_config.COLLECTIONS) - {"members"}).intersection(db.list_collection_names())


def test_existing_records_and_admin_collection_remain_intact(isolated_live_branch):
    db = isolated_live_branch
    db.create_collection("admins")
    original_admin = {"admin_id": "ADM77", "email": "admin@gym.com", "name": "Keep this admin", "password_hash": "existing-hash"}
    db.admins.insert_one(original_admin.copy())
    db.create_collection("trainers")
    original_trainer = {"trainer_id": "TRN77", "name": "Keep this trainer", "marker": "existing-record"}
    db.trainers.insert_one(original_trainer.copy())

    result = api_database.get_database()

    assert result is db
    assert db.admins.count_documents({}) == 1
    assert db.admins.find_one({"admin_id": "ADM77"})["name"] == "Keep this admin"
    assert db.admins.find_one({"admin_id": "ADM77"})["password_hash"] == "existing-hash"
    assert db.trainers.count_documents({}) == 1
    assert db.trainers.find_one({"trainer_id": "TRN77"})["marker"] == "existing-record"
    assert not (set(gym_config.COLLECTIONS) - {"trainers"}).intersection(db.list_collection_names())

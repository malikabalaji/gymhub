"""Automated checks (offline, mongomock):  python -m pytest -q"""
from datetime import datetime

import pytest

from gym_db import aggregations as A, crud as C, config
from gym_db.schema import create_collections
from gym_db.seed import seed


@pytest.fixture()
def db():
    config._client = None
    d = config.get_db(mock=True)
    create_collections(d)
    seed(d)
    from gym_db.indexes import create_indexes
    create_indexes(d)
    return d


def test_minimum_sample_records(db):
    counts = {c: db[c].count_documents({}) for c in config.COLLECTIONS}
    assert counts["members"] >= 50 and sum(counts.values()) >= 1000


def test_member_crud_and_cascade(db):
    mid = C.create_member(db, "Test User", "t.user@example.com", "9000000000",
                          datetime(2001, 1, 1), "Male", "pw", trainer_id="TRN02")
    assert C.get_member(db, mid)["name"] == "Test User"
    assert "password_hash" not in C.get_member(db, mid)
    C.create_workout_plan(db, mid, "Strength", 6, [{"day": "Mon", "exercise_name": "Squat", "sets": 3, "reps": 5}])
    C.enroll_member(db, "CLS02", mid)
    C.update_member(db, mid, name="Renamed User")
    assert db.workout_plans.find_one({"member_name": "Renamed User"})
    out = C.delete_member(db, mid)
    assert out["plans_deleted"] == 1 and C.get_member(db, mid) is None
    assert not db.classes.find_one({"enrolled_members.member_name": "Renamed User"})


def test_integrity_guards(db):
    with pytest.raises(C.IntegrityError):
        C.create_member(db, "X", "x@example.com", "9000000001", datetime(2000, 1, 1), "Male", "pw", trainer_id="TRN99")
    with pytest.raises(C.IntegrityError):
        C.delete_trainer(db, "TRN01")


def test_capacity_guard(db):
    cid = C.create_class(db, "Tiny", "Test", "TRN01", 1, [])
    active = [m["member_id"] for m in db.members.find({"membership.status": "active"}).limit(2)]
    C.enroll_member(db, cid, active[0])
    with pytest.raises(C.IntegrityError):
        C.enroll_member(db, cid, active[1])
    with pytest.raises(C.IntegrityError):
        C.enroll_member(db, cid, active[0])  # duplicate


def test_payments_flow(db):
    assert C.flag_overdue(db) > 0
    inv = C.create_invoice(db, "MEM1001", datetime(2026, 11, 1), datetime(2026, 11, 30), datetime(2026, 11, 5))
    assert C.record_payment(db, inv, "card")["status"] == "paid"
    assert C.record_payment(db, inv, "card") is None  # paid bills are immutable


def test_aggregations(db):
    rev = A.revenue_trend(db)
    paid = sum(p["amount"] for p in db.payments.find({"status": "paid"}))
    assert sum(r["total_revenue"] for r in rev) == paid
    assert len(A.class_popularity(db)) == 8
    ov = A.membership_overview(db)
    assert sum(x["count"] for x in ov["by_tier"]) == db.members.count_documents({})
    assert A.top_exercises(db)[0]["plans"] >= A.top_exercises(db)[-1]["plans"]
    top = A.top_referrers(db)[0]
    assert A.referral_network(db, top["member_id"])["network_size"] == top["network_size"]

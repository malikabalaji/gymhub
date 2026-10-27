"""Admin API tests using an isolated mongomock database."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.database import ensure_admin, get_db
from api.main import app
from gym_db import config, seed
from gym_db.indexes import create_indexes
from gym_db.schema import create_collections


@pytest.fixture(scope="module")
def mock_db():
    config._client = None
    seed.rng.seed(7731)
    db = config.get_db(mock=True)
    create_collections(db)
    seed.seed(db)
    create_indexes(db)
    ensure_admin(db)
    yield db
    seed.rng.seed(2026)


@pytest.fixture(scope="module")
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def token(client, username="admin@gym.com", password="Admin@123"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_dashboard_requires_admin_and_returns_operational_data(client):
    assert client.get("/api/admin/dashboard").status_code == 401
    member = token(client, "MEM1001", "Member@1001")
    trainer = token(client, "TRN01", "Trainer@01")
    assert client.get("/api/admin/dashboard", headers=member).status_code == 403
    assert client.get("/api/admin/dashboard", headers=trainer).status_code == 403
    response = client.get("/api/admin/dashboard", headers=token(client))
    assert response.status_code == 200
    body = response.json()
    assert body["members"] and body["trainers"] and body["classes"] and body["payments"]
    assert "password_hash" not in str(body)


def test_admin_member_management_validates_and_reuses_crud(client, mock_db):
    headers = token(client)
    assert client.post("/api/admin/members", json={"name": "Bad", "email": "invalid", "phone": "x"}, headers=headers).status_code == 422
    created = client.post("/api/admin/members", json={
        "name": "Test Admin Member", "email": "admin.member@example.test", "phone": "9876500001",
        "dob": "2000-01-01", "gender": "Other", "password": "MemberPass123", "tier": "Basic",
    }, headers=headers)
    assert created.status_code == 201, created.text
    member_id = created.json()["member_id"]
    changed = client.patch(f"/api/admin/members/{member_id}/membership", json={"tier": "Premium"}, headers=headers)
    assert changed.status_code == 200 and changed.json()["membership"]["type"] == "Premium"
    assert client.patch(f"/api/admin/members/{member_id}/membership", json={}, headers=headers).status_code == 422
    assert client.put(f"/api/admin/members/{member_id}/trainer", json={"trainer_id": "TRN01"}, headers=headers).status_code == 200
    assert mock_db.members.find_one({"member_id": member_id})["assigned_trainer_id"] is not None


def test_admin_schedule_and_billing_operations(client, mock_db):
    headers = token(client)
    assert client.post("/api/admin/classes", json={
        "class_name": "Invalid", "category": "Strength", "trainer_id": "TRN01", "capacity": 10,
        "schedule": [{"day_of_week": "Mon", "start_time": "10:00", "end_time": "09:00", "room": "A"}],
    }, headers=headers).status_code == 422
    class_res = client.post("/api/admin/classes", json={
        "class_name": "Admin Test Class", "category": "Strength", "trainer_id": "TRN01", "capacity": 10,
        "schedule": [{"day_of_week": "Mon", "start_time": "10:00", "end_time": "11:00", "room": "A"}],
    }, headers=headers)
    assert class_res.status_code == 201, class_res.text
    class_id = class_res.json()["class_id"]
    session_res = client.post(f"/api/admin/classes/{class_id}/sessions", json={"date": "2027-01-01", "start_time": "10:00", "end_time": "11:00"}, headers=headers)
    assert session_res.status_code == 201, session_res.text
    session_id = session_res.json()["session_id"]
    assert client.post(f"/api/admin/sessions/{session_id}/cancel", headers=headers).json()["status"] == "cancelled"
    assert client.post("/api/admin/invoices", json={
        "member_id": "MEM1001", "billing_period_start": "2027-01-01", "billing_period_end": "2027-01-31", "due_date": "2027-02-01",
    }, headers=headers).status_code == 201
    invoice = mock_db.payments.find_one({"member_id": mock_db.members.find_one({"member_id": "MEM1001"})["_id"], "billing_period_start": __import__("datetime").datetime(2027, 1, 1)})
    paid = client.post(f"/api/admin/invoices/{invoice['payment_id']}/record-payment", json={"mode": "UPI", "paid_on": "2027-01-02"}, headers=headers)
    assert paid.status_code == 200 and paid.json()["status"] == "paid"
    assert client.post(f"/api/admin/invoices/{invoice['payment_id']}/record-payment", json={"mode": "cash"}, headers=headers).status_code == 409


def test_admin_rejects_nonexistent_resources_and_invalid_payment(client):
    headers = token(client)
    assert client.put("/api/admin/members/MEM9999/trainer", json={"trainer_id": "TRN01"}, headers=headers).status_code == 404
    assert client.post("/api/admin/classes/CLS99/sessions", json={"date": date.today().isoformat(), "start_time": "10:00", "end_time": "11:00"}, headers=headers).status_code == 404
    assert client.post("/api/admin/invoices/PAY9999/record-payment", json={"mode": "cash"}, headers=headers).status_code == 404


def test_analytics_uses_existing_reports_and_admin_gate(client):
    assert client.get("/api/admin/analytics").status_code == 401
    assert client.get("/api/admin/analytics", headers=token(client, "MEM1001", "Member@1001")).status_code == 403
    assert client.get("/api/admin/analytics", headers=token(client, "TRN01", "Trainer@01")).status_code == 403
    response = client.get("/api/admin/analytics", headers=token(client))
    assert response.status_code == 200, response.text
    reports = response.json()
    assert reports["membership"]["by_tier"]
    assert isinstance(reports["revenue"], list)
    assert isinstance(reports["class_participation"], list)
    for key in ("at_risk_members", "outstanding_dues", "trainer_workload", "top_exercises", "peak_hours", "top_referrers"):
        assert isinstance(reports[key], list)


def test_graph_referral_report_validates_member_and_requires_admin(client):
    headers = token(client)
    response = client.get("/api/admin/analytics/referrals/MEM1001", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["member_id"] == "MEM1001"
    assert client.get("/api/admin/analytics/referrals/bad-id", headers=headers).status_code == 422
    assert client.get("/api/admin/analytics/referrals/MEM9999", headers=headers).status_code == 404
    assert client.get("/api/admin/analytics/referrals/MEM1001", headers=token(client, "MEM1001", "Member@1001")).status_code == 403


def test_analytics_handles_empty_isolated_database(client):
    import mongomock
    from api.database import ensure_admin
    from gym_db.schema import create_collections

    empty_db = mongomock.MongoClient()["gymhub_analytics_empty_test"]
    create_collections(empty_db)
    ensure_admin(empty_db)
    previous_override = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = lambda: empty_db
    try:
        with TestClient(app) as isolated_client:
            auth = token(isolated_client)
            response = isolated_client.get("/api/admin/analytics", headers=auth)
            assert response.status_code == 200, response.text
            reports = response.json()
            assert reports["membership"] == {"by_tier": [], "by_status": [], "age_groups": [], "by_city": []}
            assert reports["revenue"] == []
            assert reports["class_participation"] == []
            assert reports["top_exercises"] == []
    finally:
        app.dependency_overrides[get_db] = previous_override


def test_member_and_trainer_tokens_cannot_mutate_admin_resources(client, mock_db):
    member_headers = token(client, "MEM1001", "Member@1001")
    trainer_headers = token(client, "TRN01", "Trainer@01")
    gym_class = mock_db.classes.find_one({"class_id": {"$exists": True}})
    pending_invoice = mock_db.payments.find_one({"status": "pending"})
    assert gym_class and pending_invoice
    member_count = mock_db.members.count_documents({})
    trainer_count = mock_db.trainers.count_documents({})
    class_count = mock_db.classes.count_documents({})
    session_count = mock_db.class_sessions.count_documents({})
    payment_count = mock_db.payments.count_documents({})
    mutation_requests = [
        ("post", "/api/admin/members", {"name": "Forbidden Member", "email": "blocked@example.test", "phone": "9876500012", "dob": "2000-01-01", "gender": "Other", "password": "MemberPass123"}),
        ("post", "/api/admin/trainers", {"name": "Forbidden Trainer", "email": "blocked.trainer@example.test", "phone": "9876500013", "password": "TrainerPass123", "specialization": ["Strength"], "certification": "Test", "experience_years": 1}),
        ("post", "/api/admin/classes", {"class_name": "Forbidden Class", "category": "Strength", "trainer_id": "TRN01", "capacity": 10, "schedule": [{"day_of_week": "Mon", "start_time": "10:00", "end_time": "11:00", "room": "A"}]}),
        ("post", f"/api/admin/classes/{gym_class['class_id']}/sessions", {"date": "2027-03-01", "start_time": "10:00", "end_time": "11:00"}),
        ("post", "/api/admin/invoices", {"member_id": "MEM1001", "billing_period_start": "2027-03-01", "billing_period_end": "2027-03-31", "due_date": "2027-04-01"}),
        ("post", f"/api/admin/invoices/{pending_invoice['payment_id']}/record-payment", {"mode": "UPI"}),
    ]
    for headers in (member_headers, trainer_headers):
        for method, path, body in mutation_requests:
            response = getattr(client, method)(path, json=body, headers=headers)
            assert response.status_code == 403, f"{method.upper()} {path}: {response.status_code} {response.text}"
    assert mock_db.members.count_documents({}) == member_count
    assert mock_db.trainers.count_documents({}) == trainer_count
    assert mock_db.classes.count_documents({}) == class_count
    assert mock_db.class_sessions.count_documents({}) == session_count
    assert mock_db.payments.count_documents({}) == payment_count
    assert mock_db.payments.find_one({"payment_id": pending_invoice["payment_id"]})["status"] == "pending"

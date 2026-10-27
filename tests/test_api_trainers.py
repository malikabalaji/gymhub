"""Trainer API integration tests against an isolated in-memory MongoDB mock."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import api.database as api_database
from api.database import ensure_admin, get_db
from api.main import app
from gym_db import config as gym_config, crud, seed
from gym_db.indexes import create_indexes
from gym_db.schema import create_collections


@pytest.fixture(scope="module")
def db():
    gym_config._client = None
    seed.rng.seed(3042)
    database = gym_config.get_db(mock=True)
    create_collections(database)
    seed.seed(database)
    create_indexes(database)
    ensure_admin(database)
    yield database
    seed.rng.seed(2026)


@pytest.fixture(scope="module")
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client, username, password):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def setup_records(db):
    trainer = db.trainers.find_one({"trainer_id": "TRN01"})
    assigned = db.members.find_one({"assigned_trainer_id": trainer["_id"]})
    class_id = crud.create_class(db, "Test Strength", "Strength", "TRN01", 20, [])
    crud.enroll_member(db, class_id, assigned["member_id"])
    session_id = crud.create_session(db, class_id, datetime(2026, 10, 27), "09:00", "10:00")
    return {"trainer": trainer, "member": assigned, "class_id": class_id, "session_id": session_id}


def test_dashboard_role_gate_scope_and_real_data(client, setup_records):
    assert client.get("/api/trainers/me/dashboard").status_code == 401
    member_token = login(client, "MEM1001", "Member@1001")
    admin_token = login(client, "admin@gym.com", "Admin@123")
    assert client.get("/api/trainers/me/dashboard", headers=member_token).status_code == 403
    assert client.get("/api/trainers/me/dashboard", headers=admin_token).status_code == 403
    token = login(client, "TRN01", "Trainer@01")
    response = client.get("/api/trainers/me/dashboard?trainer_id=TRN02", headers=token)
    assert response.status_code == 200
    payload = response.json()
    assert payload["trainer"]["id"] == "TRN01"
    assert setup_records["member"]["member_id"] in {m["member_id"] for m in payload["members"]}
    assert setup_records["class_id"] in {c["class_id"] for c in payload["classes"]}
    assert setup_records["session_id"] in {s["session_id"] for s in payload["sessions"]}
    assert all("password_hash" not in member for member in payload["members"])


def test_plan_crud_validation_and_assignment_ownership(client, db, setup_records):
    token = login(client, "TRN01", "Trainer@01")
    headers = token
    member_id = setup_records["member"]["member_id"]
    plan_body = {"goal": "Strength", "duration_weeks": 6, "exercises": [
        {"day": "Mon", "exercise_name": "Squat", "sets": 3, "reps": 8, "weight_kg": 20},
        {"day": "Tue", "exercise_name": "Row", "sets": 3, "reps": 10},
    ]}
    created = client.post(f"/api/trainers/me/members/{member_id}/plans", json=plan_body, headers=headers)
    assert created.status_code == 201
    plan_id = created.json()["plan_id"]
    assert created.json()["goal"] == "Strength"
    assert client.post(f"/api/trainers/me/members/{member_id}/plans", json={**plan_body, "duration_weeks": 0}, headers=headers).status_code == 422
    assert client.post("/api/trainers/me/members/MEM9999/plans", json=plan_body, headers=headers).status_code == 404
    other = login(client, "TRN02", "Trainer@02")
    assert client.post(f"/api/trainers/me/plans/{plan_id}/exercises", json={"day":"Wed","exercise_name":"Press","sets":3,"reps":8}, headers=other).status_code == 404
    add = client.post(f"/api/trainers/me/plans/{plan_id}/exercises", json={"day":"Wed","exercise_name":"Press","sets":3,"reps":8}, headers=headers)
    assert add.status_code == 201
    progressed = client.patch(f"/api/trainers/me/plans/{plan_id}/exercises/Squat/progress", json={"add_kg":2.5}, headers=headers)
    assert progressed.status_code == 200
    squat = next(ex for ex in progressed.json()["exercises"] if ex["exercise_name"] == "Squat")
    assert squat["weight_kg"] == 22.5
    assert client.delete(f"/api/trainers/me/plans/{plan_id}/exercises/Squat", headers=headers).status_code == 200
    assert client.delete(f"/api/trainers/me/plans/{plan_id}/exercises/Row", headers=headers).status_code == 200
    assert client.delete(f"/api/trainers/me/plans/{plan_id}/exercises/Press", headers=headers).status_code == 409
    assert client.post("/api/trainers/me/plans/not-a-plan/exercises", json={"day":"Mon","exercise_name":"X","sets":3,"reps":8}, headers=headers).status_code == 422
    assert client.delete(f"/api/trainers/me/plans/{plan_id}", headers=other).status_code == 404
    assert client.delete(f"/api/trainers/me/plans/{plan_id}", headers=headers).json()["deleted"] is True


def test_attendance_success_validation_and_session_ownership(client, db, setup_records):
    token = login(client, "TRN01", "Trainer@01")
    other = login(client, "TRN02", "Trainer@02")
    member_id, session_id = setup_records["member"]["member_id"], setup_records["session_id"]
    recorded = client.post(f"/api/trainers/me/sessions/{session_id}/attendance/{member_id}", json={"status":"present","check_in_time":"09:03"}, headers=token)
    assert recorded.status_code == 200
    assert recorded.json()[0]["status"] == "present"
    revised = client.post(f"/api/trainers/me/sessions/{session_id}/attendance/{member_id}", json={"status":"late"}, headers=token)
    assert revised.status_code == 200 and revised.json()[0]["status"] == "late"
    assert db.attendance.count_documents({"session_id": db.class_sessions.find_one({"session_id": session_id})["_id"]}) == 1
    assert client.post(f"/api/trainers/me/sessions/{session_id}/attendance/{member_id}", json={"status":"unknown"}, headers=token).status_code == 422
    assert client.post(f"/api/trainers/me/sessions/{session_id}/attendance/{member_id}", json={"status":"present","check_in_time":"25:90"}, headers=token).status_code == 422
    assert client.post(f"/api/trainers/me/sessions/{session_id}/attendance/MEM9999", json={"status":"present"}, headers=token).status_code == 404
    non_enrolled = db.members.find_one({"assigned_trainer_id": setup_records["trainer"]["_id"], "_id": {"$ne": setup_records["member"]["_id"]}})
    if non_enrolled:
        response = client.post(f"/api/trainers/me/sessions/{session_id}/attendance/{non_enrolled['member_id']}", json={"status":"present"}, headers=token)
        assert response.status_code == 409
    assert client.get(f"/api/trainers/me/sessions/{session_id}/attendance", headers=other).status_code == 404
    assert client.delete(f"/api/trainers/me/sessions/{session_id}/attendance/{member_id}", headers=token).json()["deleted"] is True


@pytest.fixture
def persistent_api_mock(monkeypatch):
    """A dedicated process-local mock database served through the real get_db dependency."""
    monkeypatch.setattr(api_database, "_mock_client", None)
    monkeypatch.setattr(gym_config, "_client", None)
    monkeypatch.setattr(gym_config, "IS_MOCK", False)
    monkeypatch.setenv("USE_MOCK", "true")
    database = api_database._get_mock_database()
    seed.rng.seed(3042)
    create_collections(database)
    seed.seed(database)
    create_indexes(database)
    ensure_admin(database)
    yield database
    seed.rng.seed(2026)


def test_mock_mode_write_persists_between_api_requests(persistent_api_mock, monkeypatch):
    """A plan created by one request is visible to a later request on the stable mock client."""
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: api_database.get_database()
    try:
        with TestClient(app) as api_client:
            token = login(api_client, "TRN01", "Trainer@01")
            trainer = persistent_api_mock.trainers.find_one({"trainer_id": "TRN01"})
            member = persistent_api_mock.members.find_one({"assigned_trainer_id": trainer["_id"]})
            created = api_client.post(
                f"/api/trainers/me/members/{member['member_id']}/plans",
                headers=token,
                json={
                    "goal": "Mock persistence check",
                    "duration_weeks": 4,
                    "exercises": [{"day": "Mon", "exercise_name": "Squat", "sets": 3, "reps": 8}],
                },
            )
            assert created.status_code == 201
            plan_id = created.json()["plan_id"]

            dashboard = api_client.get("/api/trainers/me/dashboard", headers=token)
            assert dashboard.status_code == 200
            displayed_member = next(row for row in dashboard.json()["members"] if row["member_id"] == member["member_id"])
            assert displayed_member["active_plan"]["plan_id"] == plan_id

            metadata = api_client.get("/api/meta")
            assert metadata.status_code == 200
            assert metadata.json()["database_mode"] == "mock"
            assert metadata.json()["capabilities"]["transactions"]["supported"] is False
            assert metadata.json()["capabilities"]["schema_validation"]["supported"] is False
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override

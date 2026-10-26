"""Automated tests for Member Dashboard API and role/ownership security (isolated mongomock)."""
import pytest
from fastapi.testclient import TestClient

from api.database import ensure_admin, get_db
from api.main import app
from gym_db import config as gym_config
from gym_db import seed as gym_seed
from gym_db.indexes import create_indexes
from gym_db.schema import create_collections


@pytest.fixture(scope="module")
def mock_db():
    """Isolated in-memory mongomock database. Never touches live gym_db."""
    gym_config._client = None
    gym_seed.rng.seed(2026)
    d = gym_config.get_db(mock=True)
    create_collections(d)
    gym_seed.seed(d)
    create_indexes(d)
    ensure_admin(d)
    yield d
    # Restore rng seed so other test suites receive clean state
    gym_seed.rng.seed(2026)


@pytest.fixture(scope="module")
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_member_dashboard_unauthenticated(client):
    """Unauthenticated access must return 401."""
    res = client.get("/api/members/me/dashboard")
    assert res.status_code == 401


def test_member_dashboard_role_forbidden_for_admin_and_trainer(client):
    """Admin and trainer tokens must be rejected with 403 Forbidden."""
    # Admin login
    admin_login = client.post("/api/auth/login", json={"username": "admin@gym.com", "password": "Admin@123"})
    admin_token = admin_login.json()["access_token"]
    res_admin = client.get("/api/members/me/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 403

    # Trainer login
    trn_login = client.post("/api/auth/login", json={"username": "priya.menon@gym.com", "password": "Trainer@01"})
    trn_token = trn_login.json()["access_token"]
    res_trn = client.get("/api/members/me/dashboard", headers={"Authorization": f"Bearer {trn_token}"})
    assert res_trn.status_code == 403


def test_member_dashboard_success_and_data_integrity(client):
    """Member receives their own comprehensive dashboard data from existing backend queries."""
    login_res = client.post("/api/auth/login", json={"username": "MEM1001", "password": "Member@1001"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    res = client.get("/api/members/me/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    # Derived strictly from user's token
    assert data["member_id"] == "MEM1001"

    # Profile checks
    assert data["profile"]["member_id"] == "MEM1001"
    assert "password_hash" not in data["profile"]
    assert "name" in data["profile"]

    # Summary check
    assert "summary" in data
    assert data["summary"]["member_id"] == "MEM1001"
    assert "trainer" in data["summary"]

    # Workout plan check
    if data["active_plan"]:
        assert "exercises" in data["active_plan"]
        assert len(data["active_plan"]["exercises"]) >= 1

    # Enrolled classes check
    assert isinstance(data["enrolled_classes"], list)

    # Attendance check
    assert isinstance(data["recent_attendance"], list)

    # Unpaid dues check
    assert isinstance(data["unpaid_dues"], list)


def test_member_dashboard_strict_ownership(client):
    """Verifies that each member only gets their own data, preventing ID spoofing."""
    # Member 1001
    m1_login = client.post("/api/auth/login", json={"username": "MEM1001", "password": "Member@1001"})
    m1_token = m1_login.json()["access_token"]
    m1_data = client.get("/api/members/me/dashboard", headers={"Authorization": f"Bearer {m1_token}"}).json()

    # Member 1002
    m2_login = client.post("/api/auth/login", json={"username": "MEM1002", "password": "Member@1002"})
    m2_token = m2_login.json()["access_token"]
    m2_data = client.get("/api/members/me/dashboard", headers={"Authorization": f"Bearer {m2_token}"}).json()

    assert m1_data["member_id"] == "MEM1001"
    assert m2_data["member_id"] == "MEM1002"
    assert m1_data["profile"]["name"] != m2_data["profile"]["name"]

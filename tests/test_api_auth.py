"""Automated tests for API authentication, JWT issuance, and metadata (isolated mongomock)."""
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


def test_api_meta_endpoint(client):
    """Verify system metadata endpoint returns accurate configuration."""
    res = client.get("/api/meta")
    assert res.status_code == 200
    data = res.json()
    assert data["project"] == "Gym Membership Management System"
    assert data["reference_date"] == "2026-09-24"
    assert data["is_mock"] is True
    assert "collections" in data
    assert data["collections"]["members"] == 60
    assert data["collections"]["admins"] >= 1


def test_admin_login(client):
    """Test default admin can log in with bcrypt verification and receive JWT."""
    res = client.post("/api/auth/login", json={"username": "admin@gym.com", "password": "Admin@123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "admin"
    assert data["user"]["id"] == "ADM01"


def test_trainer_login_by_email_and_id(client):
    """Test trainer can log in using either email or trainer_id."""
    res_email = client.post("/api/auth/login", json={"username": "priya.menon@gym.com", "password": "Trainer@01"})
    assert res_email.status_code == 200
    assert res_email.json()["user"]["role"] == "trainer"
    assert res_email.json()["user"]["id"] == "TRN01"

    res_id = client.post("/api/auth/login", json={"username": "TRN01", "password": "Trainer@01"})
    assert res_id.status_code == 200
    assert res_id.json()["user"]["id"] == "TRN01"


def test_member_login_by_id(client):
    """Test member can log in using member ID and password."""
    res = client.post("/api/auth/login", json={"username": "MEM1001", "password": "Member@1001"})
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "member"
    assert data["user"]["id"] == "MEM1001"
    assert "access_token" in data


def test_login_invalid_credentials(client):
    """Test login fails with 401 for bad passwords or unknown users."""
    res1 = client.post("/api/auth/login", json={"username": "admin@gym.com", "password": "WrongPassword"})
    assert res1.status_code == 401

    res2 = client.post("/api/auth/login", json={"username": "nonexistent@gym.com", "password": "password"})
    assert res2.status_code == 401


def test_auth_me_endpoint(client):
    """Test /api/auth/me requires valid Bearer token and returns authenticated claims."""
    # Unauthenticated
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401

    # Invalid token
    bad_token_res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
    assert bad_token_res.status_code == 401

    # Authenticated member
    login_res = client.post("/api/auth/login", json={"username": "MEM1001", "password": "Member@1001"})
    token = login_res.json()["access_token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == "MEM1001"
    assert me_data["role"] == "member"


def test_role_routing_payload_distinction(client):
    """Confirm server returns distinct roles to enable role-specific frontend redirects."""
    # Member -> role: member -> target /member
    m = client.post("/api/auth/login", json={"username": "MEM1001", "password": "Member@1001"}).json()
    assert m["user"]["role"] == "member"

    # Trainer -> role: trainer -> target /trainer
    t = client.post("/api/auth/login", json={"username": "TRN01", "password": "Trainer@01"}).json()
    assert t["user"]["role"] == "trainer"

    # Admin -> role: admin -> target /admin
    a = client.post("/api/auth/login", json={"username": "admin@gym.com", "password": "Admin@123"}).json()
    assert a["user"]["role"] == "admin"

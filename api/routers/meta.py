"""System metadata and configuration endpoint."""
from fastapi import APIRouter, Depends
from gym_db.config import COLLECTIONS, REFERENCE_DATE, TIER_FEES, is_mock, supports_transactions

from ..database import get_db

router = APIRouter(tags=["Metadata"])


@router.get("/meta")
def get_system_metadata(db=Depends(get_db)):
    """Return system information, collection metrics, and operational capabilities."""
    coll_names = db.list_collection_names()
    counts = {}
    for c in COLLECTIONS + ["admins"]:
        if c in coll_names:
            counts[c] = db[c].count_documents({})
        else:
            counts[c] = 0

    mock_mode = is_mock()
    txn_supported = supports_transactions(db) if not mock_mode else False

    return {
        "project": "Gym Membership Management System",
        "lab": "BCSE302P - Database Systems Lab",
        "institution": "Vellore Institute of Technology",
        "review": "Review 3",
        "reference_date": REFERENCE_DATE.strftime("%Y-%m-%d"),
        "tier_fees": TIER_FEES,
        "is_mock": mock_mode,
        "database_name": db.name,
        "collections": counts,
        "capabilities": {
            "transactions": {
                "supported": txn_supported,
                "notes": "Enabled via replica set (rs0); emulated non-transactionally under mongomock" if not txn_supported else "Active on replica set",
            },
            "schema_validation": {
                "supported": not mock_mode,
                "notes": "Enforced by MongoDB $jsonSchema strict validators; skipped under mongomock" if mock_mode else "Active ($jsonSchema strict)",
            },
            "member_dashboard_view": {
                "supported": not mock_mode,
                "notes": "Stored read-only view in live MongoDB; emulated via direct aggregation under mongomock" if mock_mode else "Active read-only view",
            },
        },
        "status": "online",
    }

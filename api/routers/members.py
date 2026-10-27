"""Member domain router: member dashboard and profile operations."""
from fastapi import APIRouter, Depends, HTTPException, status
from gym_db import aggregations as gym_agg
from gym_db import crud as gym_crud

from ..database import get_db
from ..dependencies import require_role
from ..serializers import serialize_doc

router = APIRouter(prefix="/members", tags=["Members"])


@router.get("/me/dashboard")
def get_authenticated_member_dashboard(
    current_user: dict = Depends(require_role(["member"])),
    db=Depends(get_db),
):
    """Retrieve full dashboard data for the authenticated member.

    SECURITY & OWNERSHIP:
    The member ID is strictly derived from the validated JWT token (current_user['id']).
    Client-supplied IDs are not accepted or permitted here.
    """
    member_id = current_user.get("id")
    if not member_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User token does not contain a valid member ID",
        )

    # 1. Base member profile (password_hash already stripped by get_member)
    profile = gym_crud.get_member(db, member_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member profile for '{member_id}' not found",
        )

    # 2. Aggregated summary view (trainer name, tier, status, unpaid amount sum)
    summary = gym_agg.member_dashboard(db, member_id)
    if not summary:
        # Fallback if view/aggregation returned empty
        summary = {
            "member_id": member_id,
            "name": profile.get("name"),
            "tier": profile.get("membership", {}).get("type"),
            "status": profile.get("membership", {}).get("status"),
            "trainer": None,
            "unpaid_amount": 0,
        }

    # 3. Active workout plan
    active_plan = gym_crud.get_active_plan(db, member_id)

    # 4. Enrolled classes with schedule and trainer name
    enrolled_classes = gym_crud.member_classes(db, member_id)

    # 5. Last 5 attendance check-ins
    recent_attendance = gym_crud.attendance_history(db, member_id, limit=5)

    # 6. Unpaid dues / pending invoices
    unpaid_dues = gym_crud.member_dues(db, member_id)
    # Derive the headline total from the same invoice rows returned to the UI.
    # This also avoids mongomock's incomplete $sum-over-array-expression behavior.
    summary["unpaid_amount"] = sum(dues.get("amount", 0) for dues in unpaid_dues)

    return serialize_doc({
        "member_id": member_id,
        "summary": summary,
        "profile": profile,
        "active_plan": active_plan,
        "enrolled_classes": enrolled_classes,
        "recent_attendance": recent_attendance,
        "unpaid_dues": unpaid_dues,
    })

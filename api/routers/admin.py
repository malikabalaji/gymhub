"""Admin-only operational dashboard and management endpoints."""
from datetime import date, datetime, time
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from gym_db import crud as gym_crud
from gym_db import aggregations as gym_analytics

from ..database import get_db
from ..dependencies import require_role
from ..serializers import serialize_doc

router = APIRouter(prefix="/admin", tags=["Administration"])
admin_only = Depends(require_role(["admin"]))


class MemberCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str = Field(pattern=r"^\d{10}$")
    dob: date
    gender: Literal["Male", "Female", "Other"]
    password: str = Field(min_length=8, max_length=128)
    tier: Literal["Basic", "Premium", "VIP"] = "Basic"
    trainer_id: str | None = Field(default=None, pattern=r"^TRN\d{2}$")
    referred_by: str | None = Field(default=None, pattern=r"^MEM\d{4}$")
    city: str = Field(default="Vellore", min_length=2, max_length=80)
    pincode: str = Field(default="632014", pattern=r"^\d{6}$")


class MembershipUpdate(BaseModel):
    tier: Literal["Basic", "Premium", "VIP"] | None = None
    membership_status: Literal["active", "expired", "frozen"] | None = None


class TrainerAssignment(BaseModel):
    trainer_id: str = Field(pattern=r"^TRN\d{2}$")


class TrainerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str = Field(pattern=r"^\d{10}$")
    password: str = Field(min_length=8, max_length=128)
    specialization: list[str] = Field(min_length=1, max_length=10)
    certification: str = Field(min_length=2, max_length=100)
    experience_years: int = Field(ge=0, le=60)


class AvailabilityUpdate(BaseModel):
    day: Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ScheduleSlot(BaseModel):
    day_of_week: Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    room: str = Field(min_length=1, max_length=20)


class ClassCreate(BaseModel):
    class_name: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=60)
    trainer_id: str = Field(pattern=r"^TRN\d{2}$")
    capacity: int = Field(ge=1, le=50)
    schedule: list[ScheduleSlot] = Field(min_length=1, max_length=14)


class SessionCreate(BaseModel):
    date: date
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class InvoiceCreate(BaseModel):
    member_id: str = Field(pattern=r"^MEM\d{4}$")
    billing_period_start: date
    billing_period_end: date
    due_date: date


class PaymentRecord(BaseModel):
    mode: Literal["cash", "card", "UPI"]
    paid_on: date | None = None


def _not_found(message: str):
    raise HTTPException(status_code=404, detail=message)


def _integrity_error(error: Exception):
    raise HTTPException(status_code=409, detail=str(error)) from error


def _schedule_values(schedule):
    return [slot.model_dump() for slot in schedule]


@router.get("/dashboard")
def admin_dashboard(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _admin: dict = admin_only,
    db=Depends(get_db),
):
    """Return operational records and collection counts; no analytics pipelines run here."""
    members, member_count = gym_crud.list_members(db, page=page, page_size=page_size)
    trainer_docs = list(db.trainers.find({}, {"password_hash": 0}).sort("trainer_id", 1))
    trainer_ids = {doc["_id"]: doc["trainer_id"] for doc in trainer_docs}
    for member in members:
        source = db.members.find_one({"member_id": member["member_id"]}, {"assigned_trainer_id": 1})
        member["trainer_id"] = trainer_ids.get(source.get("assigned_trainer_id")) if source else None

    classes = []
    for record in db.classes.find().sort("class_id", 1):
        classes.append({
            "class_id": record["class_id"],
            "class_name": record["class_name"],
            "category": record["category"],
            "trainer_id": trainer_ids.get(record.get("trainer_id")),
            "trainer_name": record.get("trainer_name"),
            "capacity": record["capacity"],
            "enrollment_count": len(record.get("enrolled_members", [])),
            "schedule": record.get("schedule", []),
        })
    class_ids = {record["class_id"]: record["_id"] for record in db.classes.find({}, {"class_id": 1})}
    sessions = [{
        "session_id": row["session_id"],
        "class_id": next((cid for cid, oid in class_ids.items() if oid == row.get("class_id")), None),
        "class_name": row.get("class_name"),
        "date": row["date"],
        "start_time": row.get("start_time"),
        "end_time": row.get("end_time"),
        "status": row["status"],
    } for row in db.class_sessions.find().sort([("date", 1), ("start_time", 1)])]
    payments = list(db.payments.find({}, {
        "_id": 0, "payment_id": 1, "member_name": 1, "amount": 1,
        "status": 1, "due_date": 1, "payment_mode": 1,
    }).sort("due_date", 1).limit(100))
    collection_names = ("members", "trainers", "workout_plans", "classes", "class_sessions", "attendance", "payments", "admins")
    counts = {name: db[name].count_documents({}) for name in collection_names}
    return serialize_doc({
        "summary": counts,
        "members": members,
        "member_count": member_count,
        "member_page": page,
        "member_page_size": page_size,
        "trainers": [{key: value for key, value in row.items() if key != "_id"} for row in trainer_docs],
        "classes": classes,
        "sessions": sessions,
        "payments": payments,
    })


@router.get("/analytics")
def admin_analytics(_admin: dict = admin_only, db=Depends(get_db)):
    """Run the established A1–A8 and G2 reports for the admin console."""
    if db.members.count_documents({}) == 0:
        membership = {"by_tier": [], "by_status": [], "age_groups": [], "by_city": []}
    else:
        membership = gym_analytics.membership_overview(db)
    return serialize_doc({
        "membership": membership,
        "revenue": gym_analytics.revenue_trend(db),
        "class_participation": gym_analytics.class_popularity(db),
        "at_risk_members": gym_analytics.at_risk_members(db),
        "outstanding_dues": gym_analytics.outstanding_dues(db),
        "trainer_workload": gym_analytics.trainer_workload(db),
        "top_exercises": gym_analytics.top_exercises(db),
        "peak_hours": gym_analytics.peak_hours(db),
        "top_referrers": gym_analytics.top_referrers(db),
    })


@router.get("/analytics/referrals/{member_id}")
def admin_referral_network(member_id: str, _admin: dict = admin_only, db=Depends(get_db)):
    """Return the existing G1 referral traversal for a valid member code."""
    if not re.fullmatch(r"MEM\d{4}", member_id):
        raise HTTPException(status_code=422, detail="Invalid member ID")
    result = gym_analytics.referral_network(db, member_id)
    if result is None:
        _not_found("Member not found")
    return serialize_doc(result)


@router.post("/members", status_code=status.HTTP_201_CREATED)
def create_member(body: MemberCreate, _admin: dict = admin_only, db=Depends(get_db)):
    try:
        member_id = gym_crud.create_member(
            db, body.name, str(body.email), body.phone,
            datetime.combine(body.dob, time.min), body.gender, body.password,
            tier=body.tier, trainer_id=body.trainer_id, referred_by=body.referred_by,
            city=body.city, pincode=body.pincode,
        )
    except gym_crud.IntegrityError as error:
        _integrity_error(error)
    return serialize_doc(gym_crud.get_member(db, member_id))


@router.patch("/members/{member_id}/membership")
def update_membership(member_id: str, body: MembershipUpdate, _admin: dict = admin_only, db=Depends(get_db)):
    if not body.tier and not body.membership_status:
        raise HTTPException(status_code=422, detail="Provide a tier or membership_status")
    try:
        member = gym_crud.change_membership(db, member_id, tier=body.tier, status=body.membership_status)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not member:
        _not_found("Member not found")
    return serialize_doc(member)


@router.put("/members/{member_id}/trainer")
def assign_member_trainer(member_id: str, body: TrainerAssignment, _admin: dict = admin_only, db=Depends(get_db)):
    if not db.members.find_one({"member_id": member_id}, {"_id": 1}):
        _not_found("Member not found")
    try:
        changed = gym_crud.assign_trainer(db, member_id, body.trainer_id)
    except gym_crud.IntegrityError as error:
        _integrity_error(error)
    return {"member_id": member_id, "trainer_id": body.trainer_id, "changed": bool(changed)}


@router.delete("/members/{member_id}")
def delete_member(member_id: str, _admin: dict = admin_only, db=Depends(get_db)):
    try:
        result = gym_crud.delete_member(db, member_id)
    except gym_crud.IntegrityError as error:
        _integrity_error(error)
    return {"deleted": True, "member_id": member_id, **result}


@router.post("/trainers", status_code=status.HTTP_201_CREATED)
def create_trainer(body: TrainerCreate, _admin: dict = admin_only, db=Depends(get_db)):
    trainer_id = gym_crud.create_trainer(
        db, body.name, str(body.email), body.phone, body.password,
        body.specialization, body.certification, body.experience_years,
    )
    return serialize_doc(gym_crud.get_trainer(db, trainer_id))


@router.put("/trainers/{trainer_id}/availability")
def set_trainer_availability(trainer_id: str, body: AvailabilityUpdate, _admin: dict = admin_only, db=Depends(get_db)):
    if not gym_crud.get_trainer(db, trainer_id):
        _not_found("Trainer not found")
    start = datetime.strptime(body.start_time, "%H:%M")
    end = datetime.strptime(body.end_time, "%H:%M")
    if end <= start:
        raise HTTPException(status_code=422, detail="end_time must be later than start_time")
    gym_crud.set_availability(db, trainer_id, body.day, body.start_time, body.end_time)
    return serialize_doc(gym_crud.get_trainer(db, trainer_id))


@router.delete("/trainers/{trainer_id}")
def delete_trainer(trainer_id: str, _admin: dict = admin_only, db=Depends(get_db)):
    try:
        deleted = gym_crud.delete_trainer(db, trainer_id)
    except gym_crud.IntegrityError as error:
        _integrity_error(error)
    return {"deleted": bool(deleted), "trainer_id": trainer_id}


@router.post("/classes", status_code=status.HTTP_201_CREATED)
def create_class(body: ClassCreate, _admin: dict = admin_only, db=Depends(get_db)):
    if any(datetime.strptime(slot.end_time, "%H:%M") <= datetime.strptime(slot.start_time, "%H:%M") for slot in body.schedule):
        raise HTTPException(status_code=422, detail="Schedule end_time must be later than start_time")
    try:
        class_id = gym_crud.create_class(
            db, body.class_name, body.category, body.trainer_id, body.capacity, _schedule_values(body.schedule)
        )
    except gym_crud.IntegrityError as error:
        _integrity_error(error)
    return serialize_doc(gym_crud.get_class(db, class_id))


@router.delete("/classes/{class_id}")
def delete_class(class_id: str, _admin: dict = admin_only, db=Depends(get_db)):
    try:
        result = gym_crud.delete_class(db, class_id)
    except gym_crud.IntegrityError as error:
        _integrity_error(error)
    return {"deleted": True, "class_id": class_id, **result}


@router.post("/classes/{class_id}/sessions", status_code=status.HTTP_201_CREATED)
def create_class_session(class_id: str, body: SessionCreate, _admin: dict = admin_only, db=Depends(get_db)):
    if not db.classes.find_one({"class_id": class_id}, {"_id": 1}):
        _not_found("Class not found")
    if datetime.strptime(body.end_time, "%H:%M") <= datetime.strptime(body.start_time, "%H:%M"):
        raise HTTPException(status_code=422, detail="end_time must be later than start_time")
    try:
        session_id = gym_crud.create_session(
            db, class_id, datetime.combine(body.date, time.min), body.start_time, body.end_time
        )
    except gym_crud.IntegrityError as error:
        _integrity_error(error)
    return serialize_doc(db.class_sessions.find_one({"session_id": session_id}, {"_id": 0, "trainer_id": 0, "class_id": 0}))


@router.post("/sessions/{session_id}/cancel")
def cancel_class_session(session_id: str, _admin: dict = admin_only, db=Depends(get_db)):
    if not db.class_sessions.find_one({"session_id": session_id}, {"_id": 1}):
        _not_found("Session not found")
    if not gym_crud.cancel_session(db, session_id):
        raise HTTPException(status_code=409, detail="Only scheduled sessions can be cancelled")
    return {"session_id": session_id, "status": "cancelled"}


@router.post("/invoices", status_code=status.HTTP_201_CREATED)
def create_invoice(body: InvoiceCreate, _admin: dict = admin_only, db=Depends(get_db)):
    if body.billing_period_end < body.billing_period_start:
        raise HTTPException(status_code=422, detail="Billing period end must not precede start")
    if body.due_date < body.billing_period_start:
        raise HTTPException(status_code=422, detail="Due date must not precede billing period start")
    try:
        payment_id = gym_crud.create_invoice(
            db, body.member_id,
            datetime.combine(body.billing_period_start, time.min),
            datetime.combine(body.billing_period_end, time.min),
            datetime.combine(body.due_date, time.min),
        )
    except gym_crud.IntegrityError as error:
        _integrity_error(error)
    return serialize_doc(db.payments.find_one({"payment_id": payment_id}, {"_id": 0, "member_id": 0}))


@router.post("/invoices/{payment_id}/record-payment")
def record_invoice_payment(payment_id: str, body: PaymentRecord, _admin: dict = admin_only, db=Depends(get_db)):
    payment = gym_crud.record_payment(
        db, payment_id, body.mode,
        datetime.combine(body.paid_on, time.min) if body.paid_on else None,
    )
    if not payment:
        if not db.payments.find_one({"payment_id": payment_id}):
            _not_found("Invoice not found")
        raise HTTPException(status_code=409, detail="Invoice is already paid or cannot be recorded")
    return serialize_doc(payment)


@router.post("/invoices/flag-overdue")
def flag_overdue_invoices(_admin: dict = admin_only, db=Depends(get_db)):
    return {"updated": gym_crud.flag_overdue(db)}


@router.delete("/invoices/{payment_id}")
def delete_pending_invoice(payment_id: str, _admin: dict = admin_only, db=Depends(get_db)):
    if not db.payments.find_one({"payment_id": payment_id}):
        _not_found("Invoice not found")
    if not gym_crud.delete_payment(db, payment_id):
        raise HTTPException(status_code=409, detail="Only pending invoices can be deleted")
    return {"deleted": True, "payment_id": payment_id}

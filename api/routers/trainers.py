"""Trainer dashboard, workout-plan, class-session, and attendance routes."""
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from gym_db import crud as gym_crud

from ..database import get_db
from ..dependencies import require_role
from ..serializers import serialize_doc

router = APIRouter(prefix="/trainers", tags=["Trainers"])


class ExerciseInput(BaseModel):
    day: Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    exercise_name: str = Field(min_length=1, max_length=100)
    sets: int = Field(ge=1, le=50)
    reps: int = Field(ge=1, le=100)
    weight_kg: float = Field(default=0, ge=0, le=1000)
    notes: str = Field(default="", max_length=200)


class CreatePlanInput(BaseModel):
    goal: str = Field(min_length=2, max_length=80)
    duration_weeks: int = Field(ge=1, le=52)
    exercises: list[ExerciseInput] = Field(min_length=1, max_length=20)


class ProgressInput(BaseModel):
    add_kg: float = Field(gt=0, le=100)


class AttendanceInput(BaseModel):
    status: Literal["present", "absent", "late"]
    check_in_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _trainer(current_user: dict, db):
    trainer_id = current_user.get("id")
    if not isinstance(trainer_id, str) or not re.fullmatch(r"TRN\d{2}", trainer_id):
        raise HTTPException(status_code=400, detail="Token does not contain a valid trainer ID")
    trainer = gym_crud.get_trainer(db, trainer_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer profile not found")
    return trainer


def get_authenticated_trainer(
    current_user: dict = Depends(require_role(["trainer"])),
    db=Depends(get_db),
):
    """Resolve the trainer profile only from verified trainer JWT claims."""
    return _trainer(current_user, db)


def _validate_id(value: str, pattern: str, label: str):
    if not re.fullmatch(pattern, value):
        raise HTTPException(status_code=422, detail=f"Invalid {label}")


def _assigned_member(db, trainer, member_id: str):
    _validate_id(member_id, r"MEM\d{4}", "member ID")
    member = db.members.find_one({
        "member_id": member_id,
        "assigned_trainer_id": trainer["_id"],
    })
    if not member:
        # Do not reveal whether an unassigned member exists.
        raise HTTPException(status_code=404, detail="Assigned member not found")
    return member


def _owned_plan(db, trainer, plan_id: str, active_only: bool = False):
    _validate_id(plan_id, r"WP\d+", "workout plan ID")
    plan = db.workout_plans.find_one({"plan_id": plan_id})
    if not plan or plan.get("trainer_id") != trainer["_id"]:
        raise HTTPException(status_code=404, detail="Workout plan not found")
    member = db.members.find_one({
        "_id": plan.get("member_id"),
        "assigned_trainer_id": trainer["_id"],
    })
    if not member:
        raise HTTPException(status_code=404, detail="Workout plan not found")
    if active_only and plan.get("status") != "active":
        raise HTTPException(status_code=409, detail="Only active workout plans can be modified")
    return plan, member


def _owned_session(db, trainer, session_id: str):
    _validate_id(session_id, r"SES\d+", "session ID")
    session = db.class_sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")
    gym_class = db.classes.find_one({
        "_id": session.get("class_id"),
        "trainer_id": trainer["_id"],
    })
    if not gym_class:
        raise HTTPException(status_code=404, detail="Class session not found")
    return session, gym_class


def _attendance_for_sessions(db, sessions):
    if not sessions:
        return {}
    session_oids = [session["_id"] for session in sessions]
    records = list(db.attendance.find({"session_id": {"$in": session_oids}}))
    member_oids = list({record["member_id"] for record in records if record.get("member_id")})
    members = db.members.find({"_id": {"$in": member_oids}}, {"member_id": 1}) if member_oids else []
    member_ids = {member["_id"]: member["member_id"] for member in members}
    by_session = {}
    for record in records:
        member_id = member_ids.get(record.get("member_id"))
        if not member_id:
            continue
        by_session.setdefault(record["session_id"], []).append({
            "member_id": member_id,
            "member_name": record.get("member_name"),
            "status": record.get("status"),
            "date": record.get("date"),
            "check_in_time": record.get("check_in_time"),
        })
    return by_session


def _session_attendance(db, session):
    grouped = _attendance_for_sessions(db, [session])
    return grouped.get(session["_id"], [])


@router.get("/me/dashboard")
def trainer_dashboard(trainer=Depends(get_authenticated_trainer), db=Depends(get_db)):
    """Return the authenticated trainer's assigned members, plans, classes, sessions, and attendance."""
    trainer_id = trainer["_id"]
    assigned = list(db.members.find(
        {"assigned_trainer_id": trainer_id},
        {"member_id": 1},
    ).sort("member_id", 1))
    members = []
    for ref in assigned:
        profile = gym_crud.get_member(db, ref["member_id"])
        if not profile:
            continue
        members.append({
            "member_id": profile["member_id"],
            "name": profile["name"],
            "email": profile.get("email"),
            "phone": profile.get("phone"),
            "membership": profile.get("membership"),
            "city": profile.get("address", {}).get("city"),
            "active_plan": gym_crud.get_active_plan(db, profile["member_id"]),
        })

    classes = list(db.classes.find({"trainer_id": trainer_id}).sort("class_id", 1))
    class_ids = {gym_class["_id"]: gym_class["class_id"] for gym_class in classes}
    class_summaries = [{
        "class_id": gym_class["class_id"],
        "class_name": gym_class["class_name"],
        "category": gym_class.get("category"),
        "capacity": gym_class.get("capacity"),
        "enrollment_count": len(gym_class.get("enrolled_members", [])),
        "schedule": gym_class.get("schedule", []),
    } for gym_class in classes]

    sessions = list(db.class_sessions.find(
        {"class_id": {"$in": list(class_ids)}},
        {"class_id": 1, "session_id": 1, "date": 1, "start_time": 1,
         "end_time": 1, "status": 1, "class_name": 1},
    ).sort([("date", 1), ("start_time", 1)])) if class_ids else []
    attendance = _attendance_for_sessions(db, sessions)
    session_data = [{
        "session_id": session["session_id"],
        "class_id": class_ids[session["class_id"]],
        "class_name": session.get("class_name"),
        "date": session.get("date"),
        "start_time": session.get("start_time"),
        "end_time": session.get("end_time"),
        "status": session.get("status"),
        "attendance": attendance.get(session["_id"], []),
    } for session in sessions]

    return serialize_doc({
        "trainer": {
            "id": trainer["trainer_id"],
            "name": trainer["name"],
            "email": trainer.get("email"),
            "specialization": trainer.get("specialization", []),
            "certification": trainer.get("certification"),
            "experience_years": trainer.get("experience_years"),
        },
        "members": members,
        "classes": class_summaries,
        "sessions": session_data,
    })


@router.post("/me/members/{member_id}/plans", status_code=status.HTTP_201_CREATED)
def create_member_plan(
    member_id: str,
    body: CreatePlanInput,
    trainer=Depends(get_authenticated_trainer),
    db=Depends(get_db),
):
    _assigned_member(db, trainer, member_id)
    if len(body.goal.strip()) < 2 or any(not item.exercise_name.strip() for item in body.exercises):
        raise HTTPException(status_code=422, detail="Goal and exercise names must not be blank")
    gym_crud.create_workout_plan(
        db,
        member_id,
        body.goal.strip(),
        body.duration_weeks,
        [exercise.model_dump() for exercise in body.exercises],
    )
    return serialize_doc(gym_crud.get_active_plan(db, member_id))


@router.post("/me/plans/{plan_id}/exercises", status_code=status.HTTP_201_CREATED)
def add_plan_exercise(
    plan_id: str,
    body: ExerciseInput,
    trainer=Depends(get_authenticated_trainer),
    db=Depends(get_db),
):
    _owned_plan(db, trainer, plan_id, active_only=True)
    if not body.exercise_name.strip():
        raise HTTPException(status_code=422, detail="Exercise name must not be blank")
    if not gym_crud.add_exercise(db, plan_id, body.model_dump()):
        raise HTTPException(status_code=404, detail="Workout plan not found")
    return serialize_doc(db.workout_plans.find_one({"plan_id": plan_id}, {"_id": 0}))


@router.patch("/me/plans/{plan_id}/exercises/{exercise_name}/progress")
def progress_plan_exercise(
    plan_id: str,
    exercise_name: str,
    body: ProgressInput,
    trainer=Depends(get_authenticated_trainer),
    db=Depends(get_db),
):
    _owned_plan(db, trainer, plan_id, active_only=True)
    if not gym_crud.progress_exercise(db, plan_id, exercise_name, body.add_kg):
        raise HTTPException(status_code=404, detail="Exercise not found in active plan")
    return serialize_doc(db.workout_plans.find_one({"plan_id": plan_id}, {"_id": 0}))


@router.delete("/me/plans/{plan_id}/exercises/{exercise_name}")
def remove_plan_exercise(
    plan_id: str,
    exercise_name: str,
    trainer=Depends(get_authenticated_trainer),
    db=Depends(get_db),
):
    plan, _ = _owned_plan(db, trainer, plan_id, active_only=True)
    if len(plan.get("exercises", [])) <= 1:
        raise HTTPException(status_code=409, detail="A workout plan must keep at least one exercise")
    if not gym_crud.remove_exercise(db, plan_id, exercise_name):
        raise HTTPException(status_code=404, detail="Exercise not found in active plan")
    return serialize_doc(db.workout_plans.find_one({"plan_id": plan_id}, {"_id": 0}))


@router.delete("/me/plans/{plan_id}")
def delete_member_plan(
    plan_id: str,
    trainer=Depends(get_authenticated_trainer),
    db=Depends(get_db),
):
    _owned_plan(db, trainer, plan_id)
    if not gym_crud.delete_workout_plan(db, plan_id):
        raise HTTPException(status_code=404, detail="Workout plan not found")
    return {"deleted": True, "plan_id": plan_id}


@router.get("/me/sessions/{session_id}/attendance")
def get_session_attendance(
    session_id: str,
    trainer=Depends(get_authenticated_trainer),
    db=Depends(get_db),
):
    session, _ = _owned_session(db, trainer, session_id)
    return serialize_doc(_session_attendance(db, session))


@router.post("/me/sessions/{session_id}/attendance/{member_id}")
def record_session_attendance(
    session_id: str,
    member_id: str,
    body: AttendanceInput,
    trainer=Depends(get_authenticated_trainer),
    db=Depends(get_db),
):
    session, gym_class = _owned_session(db, trainer, session_id)
    member = _assigned_member(db, trainer, member_id)
    if session.get("status") == "cancelled":
        raise HTTPException(status_code=409, detail="Attendance cannot be recorded for a cancelled session")
    enrolled_ids = {entry.get("member_id") for entry in gym_class.get("enrolled_members", [])}
    if member["_id"] not in enrolled_ids:
        raise HTTPException(status_code=409, detail="Member is not enrolled in this class")
    gym_crud.mark_attendance(db, session_id, member_id, body.status, body.check_in_time)
    return serialize_doc(_session_attendance(db, session))


@router.delete("/me/sessions/{session_id}/attendance/{member_id}")
def delete_session_attendance(
    session_id: str,
    member_id: str,
    trainer=Depends(get_authenticated_trainer),
    db=Depends(get_db),
):
    session, gym_class = _owned_session(db, trainer, session_id)
    member = _assigned_member(db, trainer, member_id)
    enrolled_ids = {entry.get("member_id") for entry in gym_class.get("enrolled_members", [])}
    if member["_id"] not in enrolled_ids:
        raise HTTPException(status_code=409, detail="Member is not enrolled in this class")
    if not gym_crud.delete_attendance(db, session_id, member_id):
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return {"deleted": True, "session_id": session_id, "member_id": member_id}

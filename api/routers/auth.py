"""Authentication router: login and current-user endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..database import get_db
from ..dependencies import get_current_user
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(..., description="Email address or user ID (e.g. MEM1001, TRN01, admin@gym.com)")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def find_user_and_authenticate(db, identifier: str, password: str):
    """Authenticate against admins, trainers, and members using email or ID."""
    clean_id = identifier.strip()
    clean_email = clean_id.lower()
    clean_code = clean_id.upper()

    # 1. Check admins
    admin = db.admins.find_one({
        "$or": [{"email": clean_email}, {"admin_id": clean_code}]
    })
    if admin and verify_password(password, admin.get("password_hash", "")):
        return {
            "id": admin.get("admin_id", "ADM01"),
            "name": admin.get("name", "Administrator"),
            "email": admin.get("email", clean_email),
            "role": "admin",
        }

    # 2. Check trainers
    trainer = db.trainers.find_one({
        "$or": [{"email": clean_email}, {"trainer_id": clean_code}]
    })
    if trainer and verify_password(password, trainer.get("password_hash", "")):
        return {
            "id": trainer.get("trainer_id"),
            "name": trainer.get("name"),
            "email": trainer.get("email"),
            "role": "trainer",
        }

    # 3. Check members
    member = db.members.find_one({
        "$or": [{"email": clean_email}, {"member_id": clean_code}]
    })
    if member and verify_password(password, member.get("password_hash", "")):
        return {
            "id": member.get("member_id"),
            "name": member.get("name"),
            "email": member.get("email"),
            "role": "member",
        }

    return None


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db=Depends(get_db)):
    """Authenticate user with email or ID and password, returning JWT access token."""
    user = find_user_and_authenticate(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your email/ID and password.",
        )

    # Issue JWT token containing role, id, name, and email
    token = create_access_token(data={
        "sub": user["email"],
        "id": user["id"],
        "name": user["name"],
        "role": user["role"],
    })

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(**user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user profile derived from the validated JWT claims."""
    return UserResponse(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["sub"],
        role=current_user["role"],
    )

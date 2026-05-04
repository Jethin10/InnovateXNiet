from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import StudentProfile, User
from app.repositories.student_repository import StudentRepository
from app.schemas import (
    AuthTokenResponse,
    LoginRequest,
    RegisterStaffRequest,
    RegisterStudentRequest,
    StudentResponse,
    StaffResponse,
)


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def register_student(self, request: RegisterStudentRequest) -> StudentResponse:
        self._ensure_email_available(request.email)
        profile = StudentRepository(self.session).create_student(
            full_name=request.full_name,
            email=request.email,
            target_role=request.target_role,
            target_company=request.target_company,
            password_hash=hash_password(request.password),
        )
        return StudentResponse(
            student_id=profile.id,
            full_name=profile.user.full_name,
            email=profile.user.email,
            target_role=profile.target_role,
            target_company=profile.target_company,
        )

    def register_staff(self, request: RegisterStaffRequest) -> StaffResponse:
        if request.registration_key != self.settings.admin_registration_key:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid registration key")
        if request.role not in {"admin", "mentor"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid staff role")
        self._ensure_email_available(request.email)
        user = User(
            full_name=request.full_name,
            email=request.email.lower(),
            role=request.role,
            password_hash=hash_password(request.password),
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return StaffResponse(user_id=user.id, full_name=user.full_name, email=user.email, role=user.role)

    def login(self, request: LoginRequest) -> AuthTokenResponse:
        user = (
            self.session.query(User)
            .filter(User.email == request.email.lower())
            .one_or_none()
        )
        if user is None or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        student_id = None
        if user.role == "student":
            profile = (
                self.session.query(StudentProfile)
                .filter_by(user_id=user.id)
                .one_or_none()
            )
            student_id = profile.id if profile is not None else None
        token = create_access_token(
            {
                "sub": str(user.id),
                "role": user.role,
                "student_id": student_id,
                "email": user.email,
            },
            secret_key=self.settings.auth_secret_key,
            ttl_seconds=self.settings.access_token_ttl_seconds,
        )
        return AuthTokenResponse(
            access_token=token,
            token_type="bearer",
            role=user.role,
            student_id=student_id,
        )

    def _ensure_email_available(self, email: str) -> None:
        existing = (
            self.session.query(User)
            .filter(User.email == email.lower())
            .one_or_none()
        )
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

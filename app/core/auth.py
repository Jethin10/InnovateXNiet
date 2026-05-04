from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, status

from app.core.security import decode_access_token


STAFF_ROLES = {"admin", "mentor"}


@dataclass(frozen=True)
class ActorContext:
    role: str
    student_id: int | None = None

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES


def get_actor_context(
    request: Request,
    authorization: str | None = Header(default=None),
    x_actor_role: str | None = Header(default=None),
    x_actor_student_id: str | None = Header(default=None),
) -> ActorContext:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = decode_access_token(
            token,
            secret_key=request.app.state.settings.auth_secret_key,
        )
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
            )
        student_id = payload.get("student_id")
        return ActorContext(
            role=str(payload.get("role", "")).lower(),
            student_id=int(student_id) if student_id is not None else None,
        )

    if not x_actor_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token or actor role header",
        )

    student_id = int(x_actor_student_id) if x_actor_student_id and x_actor_student_id.isdigit() else None
    return ActorContext(role=x_actor_role.lower(), student_id=student_id)


def require_student_access(student_id: int, actor: ActorContext) -> None:
    if actor.is_staff:
        return
    if actor.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Actor cannot access student resources",
        )
    if actor.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Actor cannot access another student profile",
        )


def require_staff_access(actor: ActorContext) -> None:
    if actor.is_staff:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Staff access required",
    )

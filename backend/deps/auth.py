"""JWT 인증 및 RBAC 의존성."""
from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from backend.deps.settings import settings


class Role(str, Enum):
    """시스템에서 사용되는 사용자 역할."""

    OWNER = "owner"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    CONSUMER = "consumer"


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class UserContext(BaseModel):
    user_id: str
    role: Role


class TokenPayload(BaseModel):
    sub: str
    role: Role | None = None
    type: str
    exp: int


def create_access_token(subject: str, role: Role, expires_minutes: int = 15) -> str:
    now = dt.datetime.utcnow()
    payload = {
        "sub": subject,
        "role": role.value,
        "exp": now + dt.timedelta(minutes=expires_minutes),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(subject: str, expires_days: int = 7) -> str:
    now = dt.datetime.utcnow()
    payload = {
        "sub": subject,
        "exp": now + dt.timedelta(days=expires_days),
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def parse_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return TokenPayload.model_validate(payload)
    except JWTError as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserContext:
    payload = parse_token(token)
    if payload.type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token type")
    if payload.role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role missing")
    return UserContext(user_id=payload.sub, role=payload.role)


def require_role(*allowed_roles: Role):
    async def dependency(user: Annotated[UserContext, Depends(get_current_user)]):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user

    return dependency


__all__ = [
    "Role",
    "create_access_token",
    "create_refresh_token",
    "parse_token",
    "get_current_user",
    "require_role",
    "UserContext",
]

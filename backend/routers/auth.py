"""인증 관련 API."""
from __future__ import annotations

import base64
import hashlib

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps.auth import (
    Role,
    UserContext,
    create_access_token,
    create_refresh_token,
    get_current_user,
    parse_token,
)
from backend.deps.db import get_session
from backend.models.schema import LoginRequest, LoginResponse, TokenRefreshRequest, TokenRefreshResponse

router = APIRouter(tags=["auth"])


def _verify_password(password: str, stored: str) -> bool:
    """PBKDF2 해시 검증."""

    try:
        salt_b64, hash_b64 = stored.split(":")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except ValueError:  # pragma: no cover - 잘못된 데이터 포맷
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hashlib.compare_digest(digest, expected)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, session=Depends(get_session)):
    """이메일/비밀번호 로그인."""

    row = await session.execute(
        sa.text("SELECT id, password_hash FROM users WHERE email = :email"),
        {"email": payload.email},
    )
    user = row.fetchone()
    if not user or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    access_token = create_access_token(str(user.id), Role.OWNER)
    refresh_token = create_refresh_token(str(user.id))
    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(payload: TokenRefreshRequest):
    """리프레시 토큰으로 새 액세스 토큰 발급."""

    token_payload = parse_token(payload.refresh_token)
    if token_payload.type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")
    access_token = create_access_token(token_payload.sub, Role.OWNER)
    return TokenRefreshResponse(access_token=access_token)


@router.get("/me")
async def get_me(user: UserContext = Depends(get_current_user)):
    """현재 사용자 정보 반환."""

    return {"user_id": user.user_id, "role": user.role}

import uuid

from fastapi import APIRouter, Depends, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_current_user
from app.models.user import User
from app.schemas.auth import AuthResponse, DevLogin, GoogleLogin, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def serialize_user(user: User) -> UserOut:
    return UserOut(
        id=str(user.id), email=user.email, name=user.name, picture=user.picture, role=user.role
    )


async def upsert_user(db: AsyncSession, claims: dict) -> User:
    email = claims["email"].lower()
    user = await db.scalar(select(User).where(User.google_sub == claims["sub"]))
    role = "admin" if email == settings.super_admin_email.lower() else "user"
    if user:
        user.email = email
        user.name = claims.get("name") or email.split("@")[0]
        user.picture = claims.get("picture")
        if role == "admin":
            user.role = "admin"
    else:
        user = User(
            google_sub=claims["sub"],
            email=email,
            name=claims.get("name") or email.split("@")[0],
            picture=claims.get("picture"),
            role=role,
        )
        db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleLogin, db: AsyncSession = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="尚未設定 GOOGLE_CLIENT_ID")
    try:
        claims = id_token.verify_oauth2_token(
            payload.credential, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Google 登入驗證失敗") from exc
    if not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google 信箱尚未驗證")
    user = await upsert_user(db, claims)
    return AuthResponse(access_token=create_access_token(str(user.id)), user=serialize_user(user))


@router.post("/dev", response_model=AuthResponse)
async def dev_login(payload: DevLogin, db: AsyncSession = Depends(get_db)):
    if not settings.allow_dev_login:
        raise HTTPException(status_code=404, detail="開發登入未啟用")
    claims = {
        "sub": f"dev-{uuid.uuid5(uuid.NAMESPACE_DNS, payload.email.lower())}",
        "email": payload.email,
        "email_verified": True,
        "name": payload.name,
        "picture": None,
    }
    user = await upsert_user(db, claims)
    return AuthResponse(access_token=create_access_token(str(user.id)), user=serialize_user(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return serialize_user(user)


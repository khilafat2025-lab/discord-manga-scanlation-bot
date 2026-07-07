"""
MangaFlow AI - Authentication Endpoints
JWT + Google OAuth + GitHub OAuth + Email + Guest
"""
import httpx
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token,
    decode_token, generate_guest_token
)
from app.db.base import get_db
from app.models.models import User, UserRole, AuthProvider, AuditLog

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


async def get_or_create_oauth_user(db, email, full_name, avatar_url, provider, provider_id):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email, full_name=full_name, avatar_url=avatar_url,
            auth_provider=provider, provider_id=provider_id,
            role=UserRole.FREE, is_verified=True,
        )
        db.add(user)
        await db.flush()
    else:
        user.avatar_url = avatar_url
        user.full_name = full_name or user.full_name
    return user


def build_token_response(user):
    access_token = create_access_token(
        subject=str(user.id),
        extra_data={"role": user.role.value, "email": user.email},
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": str(user.id), "email": user.email, "full_name": user.full_name,
            "avatar_url": user.avatar_url, "role": user.role.value,
            "is_verified": user.is_verified, "pages_used_today": user.pages_used_today,
            "total_pages_processed": user.total_pages_processed,
        },
    )


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email, full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        auth_provider=AuthProvider.EMAIL, role=UserRole.FREE,
    )
    db.add(user)
    await db.flush()
    db.add(AuditLog(user_id=user.id, action="register", resource_type="user"))
    return build_token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    db.add(AuditLog(user_id=user.id, action="login", resource_type="user"))
    return build_token_response(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return build_token_response(user)


@router.post("/guest")
async def guest_login():
    token = generate_guest_token()
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": "guest", "email": None, "full_name": "Guest User", "role": "guest", "pages_used_today": 0},
    }


@router.get("/google")
async def google_login():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")
    params = f"client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={settings.GOOGLE_REDIRECT_URI}&response_type=code&scope=openid email profile&access_type=offline"
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")
    async with httpx.AsyncClient() as client:
        token_resp = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code, "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI, "grant_type": "authorization_code",
        })
        token_data = token_resp.json()
        user_resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"})
        user_info = user_resp.json()
    user = await get_or_create_oauth_user(db, user_info["email"], user_info.get("name",""),
        user_info.get("picture",""), AuthProvider.GOOGLE, user_info["id"])
    tokens = build_token_response(user)
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?access_token={tokens.access_token}&refresh_token={tokens.refresh_token}")


@router.get("/github")
async def github_login():
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
    return RedirectResponse(f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&redirect_uri={settings.GITHUB_REDIRECT_URI}&scope=user:email")


@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
    async with httpx.AsyncClient() as client:
        token_resp = await client.post("https://github.com/login/oauth/access_token",
            data={"client_id": settings.GITHUB_CLIENT_ID, "client_secret": settings.GITHUB_CLIENT_SECRET, "code": code},
            headers={"Accept": "application/json"})
        access_token = token_resp.json().get("access_token")
        user_resp = await client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {access_token}"})
        user_info = user_resp.json()
        email_resp = await client.get("https://api.github.com/user/emails", headers={"Authorization": f"Bearer {access_token}"})
        emails = email_resp.json()
        primary_email = next((e["email"] for e in emails if e.get("primary") and e.get("verified")), user_info.get("email"))
    user = await get_or_create_oauth_user(db, primary_email, user_info.get("name") or user_info.get("login",""),
        user_info.get("avatar_url",""), AuthProvider.GITHUB, str(user_info["id"]))
    tokens = build_token_response(user)
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?access_token={tokens.access_token}&refresh_token={tokens.refresh_token}")


@router.get("/me")
async def get_me(request: Request, db: AsyncSession = Depends(get_db)):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(auth.split(" ")[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    if user_id and user_id.startswith("guest_"):
        return {"id": user_id, "role": "guest", "email": None}
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id), "email": user.email, "full_name": user.full_name,
        "avatar_url": user.avatar_url, "role": user.role.value,
        "is_verified": user.is_verified, "pages_used_today": user.pages_used_today,
        "total_pages_processed": user.total_pages_processed,
        "created_at": user.created_at.isoformat(),
    }

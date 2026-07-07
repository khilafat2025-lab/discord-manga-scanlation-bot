"""
MangaFlow AI - Security: JWT, Password Hashing, API Keys
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import secrets
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[dict] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "type": "access", "iat": datetime.now(timezone.utc)}
    if extra_data:
        to_encode.update(extra_data)
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: Union[str, int]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh", "iat": datetime.now(timezone.utc)}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str]:
    raw_key = f"mf_{secrets.token_urlsafe(32)}"
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, hashed


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    return hashlib.sha256(raw_key.encode()).hexdigest() == hashed_key


def generate_guest_token() -> str:
    guest_id = f"guest_{secrets.token_urlsafe(16)}"
    return create_access_token(subject=guest_id, expires_delta=timedelta(hours=24), extra_data={"role": "guest"})

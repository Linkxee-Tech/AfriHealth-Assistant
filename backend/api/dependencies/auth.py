"""
Authentication dependencies and utilities.
"""
from datetime import datetime, timedelta
from typing import Optional
import os
import secrets
from pathlib import Path
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.database.db_manager import db_manager
from backend.config import resolve_project_path, settings

def _load_secret_key() -> str:
    """Load a configured JWT secret or create a persistent local secret."""
    configured = os.getenv("SECRET_KEY", "").strip()
    if configured and configured != "change-this-in-a-local-secrets-file":
        return configured

    secret_path = resolve_project_path(settings.DB_PATH).expanduser().resolve().parent / ".secret_key"
    try:
        if secret_path.exists():
            value = secret_path.read_text(encoding="utf-8").strip()
            if value:
                return value
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        value = secrets.token_urlsafe(48)
        secret_path.write_text(value, encoding="utf-8")
        try:
            secret_path.chmod(0o600)
        except OSError:
            pass
        return value
    except OSError as exc:
        raise RuntimeError(
            "SECRET_KEY is not configured and a persistent local secret could not be created. "
            "Set SECRET_KEY in .env before starting the backend."
        ) from exc


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = db_manager.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user

async def optional_api_key():
    return True

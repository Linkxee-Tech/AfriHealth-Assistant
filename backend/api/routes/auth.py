from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from datetime import timedelta
from email.message import EmailMessage
import smtplib
import secrets

from backend.api.dependencies.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)
from backend.database.db_manager import db_manager
from backend.config import settings

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    email: str | None = Field(None, max_length=255)

class ForgotPasswordRequest(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50)
    email: str | None = Field(None, max_length=255)

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=8)
    new_password: str = Field(..., min_length=8, max_length=128)

class AdminRecoveryRequest(BaseModel):
    admin_token: str = Field(..., min_length=16, max_length=256)
    username: str = Field(..., min_length=3, max_length=50)
    new_password: str = Field(..., min_length=8, max_length=128)

class Token(BaseModel):
    access_token: str
    token_type: str

@auth_router.post("/register", response_model=Token)
async def register(user: UserCreate):
    db_user = db_manager.get_user_by_username(user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    if user.email and db_manager.get_user_by_email(user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_manager.create_user(user.username, hashed_password, email=user.email)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db_manager.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact an administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.get("/me")
async def read_users_me(current_user = Depends(get_current_user)):
    return {"username": current_user.username, "email": current_user.email, "id": current_user.id, "is_admin": bool(getattr(current_user, "is_admin", False))}


def _send_reset_email(recipient: str, token: str) -> bool:
    if not all((settings.SMTP_HOST, settings.SMTP_FROM, recipient)):
        return False
    message = EmailMessage()
    message["Subject"] = "AfriHealth Assistant password reset"
    message["From"] = settings.SMTP_FROM
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your AfriHealth Assistant account.\n\n"
        f"Use this one-time token with POST /auth/reset-password: {token}\n"
        f"It expires in {settings.PASSWORD_RESET_TTL_MINUTES} minutes."
    )
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        return False


@auth_router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Start password recovery without disclosing whether an account exists."""
    if not request.username and not request.email:
        raise HTTPException(status_code=400, detail="Username or email is required")
    identity = request.username or request.email
    reset = db_manager.create_password_reset(
        username=request.username,
        email=request.email,
        ttl_minutes=settings.PASSWORD_RESET_TTL_MINUTES,
    )
    response = {"success": True, "message": "If the account exists, recovery instructions have been prepared."}
    if reset:
        if _send_reset_email(reset.get("email"), reset["token"]):
            response["delivery"] = "email"
        elif settings.AUTH_RECOVERY_MODE.lower() == "local":
            # Explicitly local-only: useful for offline deployments and never
            # enabled as a silent email substitute in email mode.
            response["delivery"] = "local"
            response["recovery_token"] = reset["token"]
        else:
            response["delivery"] = "unavailable"
    return response


@auth_router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    if not db_manager.consume_password_reset(request.token, get_password_hash(request.new_password)):
        raise HTTPException(status_code=400, detail="The recovery token is invalid or expired")
    return {"success": True, "message": "Password reset successfully. You can now sign in."}


@auth_router.post("/admin-recover")
async def admin_recover_password(request: AdminRecoveryRequest):
    """Explicit local administrator recovery for accounts with no email."""
    configured = settings.PASSWORD_RESET_ADMIN_TOKEN.strip()
    if not configured or not secrets.compare_digest(request.admin_token, configured):
        raise HTTPException(status_code=403, detail="Administrator recovery is not configured or the token is invalid")
    reset = db_manager.create_password_reset(username=request.username, ttl_minutes=settings.PASSWORD_RESET_TTL_MINUTES)
    if not reset or not db_manager.consume_password_reset(reset["token"], get_password_hash(request.new_password)):
        raise HTTPException(status_code=400, detail="User account not found")
    return {"success": True, "message": "Password reset successfully. The user can now sign in."}

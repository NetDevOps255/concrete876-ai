"""
Auth router — login endpoint.
POST /auth/login  → returns JWT access token
GET  /auth/me     → returns current user info
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from passlib.context import CryptContext

from core.config import settings
from core.auth import create_access_token, require_auth

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    """
    Authenticate with username + password.
    Returns a JWT that the UI stores in sessionStorage.
    """
    if not settings.admin_password_hash:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No admin password configured. Set ADMIN_PASSWORD_HASH in .env — see README.",
        )

    username_ok = secrets_compare(data.username, settings.admin_username)
    password_ok = pwd_context.verify(data.password, settings.admin_password_hash)

    if not username_ok or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": data.username})
    return TokenResponse(access_token=token)


@router.get("/me")
def me(auth=Depends(require_auth)):
    return {"authenticated": True, "method": auth.get("method"), "user": auth.get("sub", "api")}


# constant-time string comparison to avoid timing attacks on username
import secrets as _secrets
def secrets_compare(a: str, b: str) -> bool:
    return _secrets.compare_digest(a.encode(), b.encode())

"""
Authentication — API Key + optional JWT session tokens.
All API routes are protected. The UI uses a single API key stored in .env.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from pydantic import BaseModel

from core.config import settings

# ─── Schemes ──────────────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ─── API Key auth (simple, for curl / external integrations) ─────────────────

def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> bool:
    """Constant-time compare to prevent timing attacks."""
    if not settings.api_key:
        return False
    return secrets.compare_digest(api_key or "", settings.api_key)


# ─── JWT token auth (for UI session) ─────────────────────────────────────────

class TokenData(BaseModel):
    sub: str


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_jwt(credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[TokenData]:
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        sub = payload.get("sub")
        if not sub:
            return None
        return TokenData(sub=sub)
    except JWTError:
        return None


# ─── Unified dependency ───────────────────────────────────────────────────────

def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
):
    """
    Accepts either:
    - Bearer <JWT token>   (UI session)
    - X-API-Key <key>      (API / curl access)

    Raises 401 if neither is valid.
    """
    # Check API key first (fast path)
    if api_key and settings.api_key:
        if secrets.compare_digest(api_key, settings.api_key):
            return {"method": "api_key"}

    # Check JWT
    token_data = verify_jwt(credentials)
    if token_data:
        return {"method": "jwt", "sub": token_data.sub}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

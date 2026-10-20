import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.database import db

security = HTTPBearer(auto_error=False)

def create_jwt_token(payload: Dict[str, Any], expires_hours: int = 24) -> str:
    """Creates a signed JWT token."""
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    token = jwt.encode(to_encode, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    return token

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again."
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """Extracts and verifies the current authenticated user from Bearer header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )
    
    token = credentials.credentials

    # If Supabase is connected, we can verify with Supabase Auth or decode JWT
    if db.is_supabase_connected and db.client:
        try:
            user_response = db.client.auth.get_user(token)
            if user_response and user_response.user:
                user = user_response.user
                # Fetch role from profiles table
                profile_res = db.client.table("profiles").select("*").eq("id", user.id).execute()
                profile = profile_res.data[0] if profile_res.data else {}
                return {
                    "id": user.id,
                    "email": user.email,
                    "full_name": profile.get("full_name") or user.user_metadata.get("full_name", ""),
                    "phone_number": profile.get("phone_number") or user.user_metadata.get("phone_number", ""),
                    "role": profile.get("role", "user")
                }
        except Exception:
            pass # Fall back to local JWT decode

    payload = decode_jwt_token(token)
    user_id = payload.get("sub") or payload.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing user identifier."
        )

    profile = db._profiles.get(user_id)
    if profile:
        return {
            "id": profile["id"],
            "email": profile["email"],
            "full_name": profile.get("full_name", ""),
            "phone_number": profile.get("phone_number", ""),
            "role": profile.get("role", "user")
        }

    return {
        "id": user_id,
        "email": payload.get("email", ""),
        "full_name": payload.get("full_name", ""),
        "phone_number": payload.get("phone_number", ""),
        "role": payload.get("role", "user")
    }

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """Allows anonymous callers or returns user if valid Bearer token provided."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None

def get_current_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Guards endpoints so only accounts with role='admin' can proceed."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privileges required."
        )
    return current_user

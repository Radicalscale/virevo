from fastapi import HTTPException, status, Request
from typing import Optional
from auth_utils import decode_access_token

async def get_current_user(request: Request) -> dict:
    """
    Extract and validate JWT token from httpOnly cookie.
    Returns user info if valid, raises 401 if invalid/missing.
    """
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return {
        "id": payload.get("sub"),
        "email": payload.get("email")
    }

async def get_optional_user(request: Request) -> Optional[dict]:
    """
    Extract and validate JWT token from httpOnly cookie.
    Returns user info if valid, None if invalid/missing.
    Used for routes that can work with or without auth.
    """
    token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    payload = decode_access_token(token)
    
    if not payload:
        return None
    
    return {
        "id": payload.get("sub"),
        "email": payload.get("email")
    }

import os
import jwt
from typing import Dict, Any
import requests
from functools import lru_cache

class AuthService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.supabase_service_key:
            raise ValueError("Missing Supabase configuration")
    
    @lru_cache(maxsize=1)
    def get_supabase_jwt_secret(self) -> str:
        """Get JWT secret from Supabase"""
        # In production, this should be the actual JWT secret
        # For now, we'll use the service key (not recommended for production)
        return self.supabase_service_key
    
    def verify_supabase_jwt(self, token: str) -> Dict[str, Any]:
        """Verify Supabase JWT token"""
        try:
            # For development, we'll skip verification and decode without verification
            # In production, you should properly verify the JWT with Supabase's public key
            payload = jwt.decode(
                token, 
                options={"verify_signature": False}  # Only for development!
            )
            return payload
        except jwt.InvalidTokenError:
            raise ValueError("Invalid JWT token")

# Create singleton instance
auth_service = AuthService()

def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """Helper function to verify JWT token"""
    return auth_service.verify_supabase_jwt(token)

# backend/src/middleware/auth_middleware.py
from fastapi import HTTPException, Header, Depends
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from backend.src.database.core.database import get_db
from backend.src.database.core.models import User
from backend.src.services.auth_service import verify_supabase_jwt

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user from JWT token"""
    if not authorization:
        return None
    
    try:
        token = authorization.replace("Bearer ", "")
        jwt_payload = verify_supabase_jwt(token)
        auth_user_id = jwt_payload.get("sub")
        
        if not auth_user_id:
            return None
        
        user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
        return user
        
    except Exception:
        return None

async def require_auth(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """Require authentication - raises 401 if not authenticated"""
    try:
        token = authorization.replace("Bearer ", "")
        jwt_payload = verify_supabase_jwt(token)
        auth_user_id = jwt_payload.get("sub")
        
        if not auth_user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed")

def require_roles(allowed_roles: list):
    """Decorator to require specific user roles"""
    def decorator(user: User = Depends(require_auth)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return user
    return decorator
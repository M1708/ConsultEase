from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from src.database.core.database import get_db
from src.database.core.models import User
from src.services.auth_service import verify_supabase_jwt
from datetime import datetime
import uuid

# Simple in-memory cache for user profiles (5 minute TTL)
_user_profile_cache = {}
_cache_ttl = 300  # 5 minutes

router = APIRouter()

@router.get("/profile/{auth_user_id}")
async def get_user_profile(
    auth_user_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get user profile by Supabase auth user ID"""
    try:
        # Check cache first
        cache_key = f"profile:{auth_user_id}"
        if cache_key in _user_profile_cache:
            cached_data, timestamp = _user_profile_cache[cache_key]
            if datetime.utcnow().timestamp() - timestamp < _cache_ttl:
                return cached_data
            else:
                # Remove expired cache entry
                del _user_profile_cache[cache_key]
        
        # Verify the JWT token if provided
        if authorization:
            token = authorization.replace("Bearer ", "")
            jwt_payload = verify_supabase_jwt(token)
            
            # Ensure the requesting user matches the profile being requested
            if jwt_payload.get("sub") != auth_user_id:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Find user by auth_user_id
        temp = await db.execute(select(User).filter(User.auth_user_id == auth_user_id))
        user = temp.scalar_one_or_none()
        ###user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        profile_data = {
            "user_id": str(user.user_id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "role": user.role,
            "status": user.status,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "department": user.department,
            "job_title": user.job_title,
            "hire_date": user.hire_date.isoformat() if user.hire_date else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "password_reset_required": user.password_reset_required,
            "two_factor_enabled": user.two_factor_enabled,
            "preferences": user.preferences or {},
            "permissions": user.permissions or {},
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat()
        }
        
        # Cache the result
        _user_profile_cache[cache_key] = (profile_data, datetime.utcnow().timestamp())
        
        return profile_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")

@router.patch("/users/{user_id}/last-login")
async def update_last_login(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Update user's last login timestamp"""
    try:
        if authorization:
            token = authorization.replace("Bearer ", "")
            verify_supabase_jwt(token)
        
        temp = await db.execute(select(User).filter(User.user_id == user_id))
        user = temp.scalar_one_or_none()
        ###user = db.query(User).filter(User.user_id == user_id).first()
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.last_login = datetime.utcnow()
        await db.commit()
        
        return {"message": "Last login updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update last login: {str(e)}")

@router.get("/me")
async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user"""
    try:
        token = authorization.replace("Bearer ", "")
        jwt_payload = verify_supabase_jwt(token)
        auth_user_id = jwt_payload.get("sub")
        
        if not auth_user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        temp = await db.execute(select(User).filter(User.auth_user_id == auth_user_id))
        user = temp.scalar_one_or_none()
        ###user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user_id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "status": user.status
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")
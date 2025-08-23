from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from backend.src.database.core.database import get_db
from backend.src.database.core.models import User
from backend.src.services.auth_service import verify_supabase_jwt
from datetime import datetime
import uuid

router = APIRouter()

@router.get("/profile/{auth_user_id}")
async def get_user_profile(
    auth_user_id: str,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get user profile by Supabase auth user ID"""
    try:
        # Verify the JWT token if provided
        if authorization:
            token = authorization.replace("Bearer ", "")
            jwt_payload = verify_supabase_jwt(token)
            
            # Ensure the requesting user matches the profile being requested
            if jwt_payload.get("sub") != auth_user_id:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Find user by auth_user_id
        user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return {
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")

@router.patch("/users/{user_id}/last-login")
async def update_last_login(
    user_id: str,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Update user's last login timestamp"""
    try:
        if authorization:
            token = authorization.replace("Bearer ", "")
            verify_supabase_jwt(token)
        
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.last_login = datetime.utcnow()
        db.commit()
        
        return {"message": "Last login updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update last login: {str(e)}")

@router.get("/me")
async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    try:
        token = authorization.replace("Bearer ", "")
        jwt_payload = verify_supabase_jwt(token)
        auth_user_id = jwt_payload.get("sub")
        
        if not auth_user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
        
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
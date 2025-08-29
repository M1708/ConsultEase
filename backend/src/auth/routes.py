from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database.core.database import get_db
from src.database.core.models import User
from src.auth.dependencies import get_current_user, AuthenticatedUser
from src.auth.session_manager import SessionManager
from src.auth.schemas import UserProfileResponse
from pydantic import BaseModel

router = APIRouter()
session_manager = SessionManager()

class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    email: str
    role: str
    created_at: str
    last_accessed: str

@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get current user's profile"""
    return UserProfileResponse(
        user_id=str(current_user.user.user_id),
        email=current_user.user.email,
        first_name=current_user.user.first_name,
        last_name=current_user.user.last_name,
        role=current_user.user.role.value,
        status=current_user.user.status.value,
        phone=current_user.user.phone,
        last_login=current_user.user.last_login,
        two_factor_enabled=current_user.user.two_factor_enabled,
        preferences=current_user.user.preferences,
        created_at=current_user.user.created_at,
        updated_at=current_user.user.updated_at
    )

@router.get("/profile/{user_id}", response_model=UserProfileResponse)
async def get_user_profile_by_id(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user profile by user ID (for internal use)"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserProfileResponse(
        user_id=str(user.user_id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        status=user.status.value,
        phone=user.phone,
        last_login=user.last_login,
        two_factor_enabled=user.two_factor_enabled,
        preferences=user.preferences,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@router.patch("/users/{user_id}/last-login")
async def update_last_login(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Update user's last login timestamp"""
    from datetime import datetime
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {"message": "Last login updated successfully"}

@router.get("/session", response_model=SessionResponse)
async def get_current_session(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get current session information"""
    session_data = await session_manager.get_session(
        current_user.session_id, 
        str(current_user.user_id)
    )
    
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return SessionResponse(**session_data)

@router.post("/logout")
async def logout(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Logout current user and invalidate session"""
    await session_manager.invalidate_session(
        current_user.session_id,
        str(current_user.user_id)
    )
    
    return {"message": "Logged out successfully"}

@router.get("/debug/sessions")
async def debug_redis_sessions():
    """Debug endpoint to check Redis sessions"""
    try:
        # Get all session keys
        session_keys = session_manager.redis_client.keys("session:*")
        
        # Get session data for each key
        sessions = []
        for key in session_keys:
            session_data = session_manager.redis_client.get(key)
            if session_data:
                import json
                sessions.append({
                    "key": key,
                    "data": json.loads(session_data)
                })
        
        return {
            "total_sessions": len(sessions),
            "session_keys": session_keys,
            "sessions": sessions
        }
    except Exception as e:
        return {"error": str(e)}
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database.core.database import get_db
from src.auth.dependencies import get_current_user, AuthenticatedUser
from src.auth.session_manager import SessionManager
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

router = APIRouter()
session_manager = SessionManager()

class ChatSessionCreate(BaseModel):
    session_id: str
    user_id: str
    chat_data: Dict[str, Any]

class ChatSessionResponse(BaseModel):
    session_id: str
    user_id: str
    chat_data: Dict[str, Any]
    created_at: str
    last_accessed: str

@router.post("/session", response_model=Dict[str, str])
async def store_chat_session(
    request: ChatSessionCreate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Store chat session data in Redis"""
    # Verify user can only store their own session
    if request.user_id != str(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot store session for different user"
        )
    
    try:
        await session_manager.store_chat_session(
            request.session_id,
            request.user_id,
            request.chat_data
        )
        return {"message": "Chat session stored successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store chat session: {str(e)}"
        )

@router.get("/session/{session_id}")
async def get_chat_session(
    session_id: str,
    user_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get chat session data from Redis"""
    # Verify user can only access their own session
    if user_id != str(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access session for different user"
        )
    
    try:
        chat_data = await session_manager.get_chat_session(session_id, user_id)
        if not chat_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        return chat_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat session: {str(e)}"
        )
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from supabase import create_client, Client
from src.database.core.database import get_db
from src.database.core.models import User
from src.auth.session_manager import SessionManager
from datetime import datetime
import os

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

security = HTTPBearer()
session_manager = SessionManager()

class AuthenticatedUser:
    def __init__(self, user: User, session_id: str):
        self.user = user
        self.session_id = session_id
        self.user_id = user.user_id
        self.email = user.email
        self.role = user.role
        self.status = user.status

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AuthenticatedUser:
    """Get current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        
        # Verify JWT token with Supabase
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        auth_user = response.user
        
        # Get user profile from database - profile_id equals auth user id
        temp = await db.execute(select(User).filter(User.user_id == auth_user.id))
        user = temp.scalar_one_or_none()
        #user = db.query(User).filter(User.user_id == auth_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Check user status
        if user.status != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User account is {user.status}"
            )
        
        # Get or create session - using profile_id for both parameters since they're the same
        session_id = await session_manager.get_or_create_session(
            user_id=str(user.user_id),
            auth_user_id=str(user.user_id),  # Same as user_id since profile_id = auth user id
            email=user.email,
            role=user.role.value
        )
        
        # Update last login
        
        user.last_login = datetime.utcnow()
        await db.commit()
        
        return AuthenticatedUser(user, session_id)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
    
async def require_admin(current_user: AuthenticatedUser = Depends(get_current_user)):
    if current_user.role not in ['super_admin', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_manager_or_above(current_user: AuthenticatedUser = Depends(get_current_user)):
    if current_user.role not in ['super_admin', 'admin', 'manager']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access or above required"
        )
    return current_user
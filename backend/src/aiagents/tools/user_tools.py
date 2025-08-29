from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.database.core.models import User, UserRole, UserStatus # Assuming Profile is the User model
from src.database.core.schemas import UserCreate, UserUpdate, UserResponse # Assuming these are the user schemas

# --- Pydantic Schemas for Tool Parameters and Responses ---

class UserToolResult(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

class CreateUserParams(BaseModel):
    email: str = Field(..., description="Email address of the new user")
    first_name: Optional[str] = Field(None, description="First name of the user")
    last_name: Optional[str] = Field(None, description="Last name of the user")
    role: UserRole = Field(UserRole.viewer, description="Role of the user (e.g., super_admin, admin, manager, employee, client, viewer)")
    status: UserStatus = Field(UserStatus.active, description="Status of the user (e.g., active, inactive, suspended, pending)")

class UpdateUserParams(BaseModel):
    profile_id: str = Field(..., description="UUID of the user profile to update")
    email: Optional[str] = Field(None, description="New email address for the user")
    first_name: Optional[str] = Field(None, description="New first name for the user")
    last_name: Optional[str] = Field(None, description="New last name for the user")
    role: Optional[UserRole] = Field(None, description="New role for the user")
    status: Optional[UserStatus] = Field(None, description="New status for the user")

class SearchUsersParams(BaseModel):
    query: Optional[str] = Field(None, description="Search query for user email, first name, or last name")
    role: Optional[UserRole] = Field(None, description="Filter users by role")
    status: Optional[UserStatus] = Field(None, description="Filter users by status")
    limit: int = Field(10, description="Maximum number of results to return")

class GetUserDetailsParams(BaseModel):
    profile_id: str = Field(..., description="UUID of the user profile to retrieve details for")

class DeleteUserParams(BaseModel):
    profile_id: str = Field(..., description="UUID of the user profile to delete")

# --- Tool Functions ---

def create_user_tool(params: CreateUserParams, db: Session) -> UserToolResult:
    try:
        # Check if user with email already exists
        existing_user = db.query(User).filter(User.email == params.email).first()
        if existing_user:
            return UserToolResult(success=False, message=f"User with email {params.email} already exists.")

        new_profile_data = params.model_dump(exclude_unset=True)
        new_profile = User(**new_profile_data)
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return UserToolResult(success=True, message="User created successfully.", data=ProfileResponse.model_validate(new_profile).model_dump())
    except Exception as e:
        db.rollback()
        return UserToolResult(success=False, message=f"Error creating user: {e}")

def get_user_details_tool(params: GetUserDetailsParams, db: Session) -> UserToolResult:
    try:
        user = db.query(User).filter(User.profile_id == params.profile_id).first()
        if not user:
            return UserToolResult(success=False, message="User not found.")
        return UserToolResult(success=True, message="User details retrieved successfully.", data=ProfileResponse.model_validate(user).model_dump())
    except Exception as e:
        return UserToolResult(success=False, message=f"Error retrieving user details: {e}")

def update_user_tool(params: UpdateUserParams, db: Session) -> UserToolResult:
    try:
        user = db.query(User).filter(User.profile_id == params.profile_id).first()
        if not user:
            return UserToolResult(success=False, message="User not found.")

        update_data = params.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        return UserToolResult(success=True, message="User updated successfully.", data=ProfileResponse.model_validate(user).model_dump())
    except Exception as e:
        db.rollback()
        return UserToolResult(success=False, message=f"Error updating user: {e}")

def delete_user_tool(params: DeleteUserParams, db: Session) -> UserToolResult:
    try:
        user = db.query(User).filter(User.profile_id == params.profile_id).first()
        if not user:
            return UserToolResult(success=False, message="User not found.")
        
        db.delete(user)
        db.commit()
        return UserToolResult(success=True, message="User deleted successfully.")
    except Exception as e:
        db.rollback()
        return UserToolResult(success=False, message=f"Error deleting user: {e}")

def search_users_tool(params: SearchUsersParams, db: Session) -> UserToolResult:
    try:
        query = db.query(User)
        if params.query:
            search_term = f"%{params.query.lower()}%"
            query = query.filter(
                (User.email.ilike(search_term)) |
                (User.first_name.ilike(search_term)) |
                (User.last_name.ilike(search_term))
            )
        if params.role:
            query = query.filter(User.role == params.role)
        if params.status:
            query = query.filter(User.status == params.status)
        
        users = query.limit(params.limit).all()
        return UserToolResult(success=True, message="Users retrieved successfully.", data=[ProfileResponse.model_validate(user).model_dump() for user in users])
    except Exception as e:
        return UserToolResult(success=False, message=f"Error searching users: {e}")

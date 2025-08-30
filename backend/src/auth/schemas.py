from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, Dict, Any

class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str] = None
    role: str
    status: str
    phone: Optional[str]
    last_login: Optional[datetime]
    two_factor_enabled: bool
    preferences: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
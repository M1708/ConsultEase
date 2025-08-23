from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, Dict, Any

class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    status: str
    phone: Optional[str]
    last_login: Optional[datetime]
    two_factor_enabled: bool
    preferences: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email
    
    class Config:
        from_attributes = True
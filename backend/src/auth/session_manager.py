import redis
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

class SessionManager:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("REDIS_URL environment variable required")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.session_ttl = int(os.getenv("SESSION_TTL", "86400"))  # 24 hours
        
    async def get_or_create_session(
        self, 
        user_id: str, 
        auth_user_id: str,  # Same value as user_id, but keeping for API compatibility
        email: str, 
        role: str
    ) -> str:
        """Get existing session or create new one"""
        # Check for existing session
        existing_sessions = self.redis_client.keys(f"session:*:user:{user_id}")
        
        for session_key in existing_sessions:
            session_data = self.redis_client.get(session_key)
            if session_data:
                data = json.loads(session_data)
                # Extend session TTL
                self.redis_client.expire(session_key, self.session_ttl)
                return data['session_id']
        
        # Create new session
        session_id = str(uuid.uuid4())
        session_key = f"session:{session_id}:user:{user_id}"
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "email": email,
            "role": role,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat()
        }
        
        self.redis_client.setex(
            session_key, 
            self.session_ttl, 
            json.dumps(session_data)
        )
        
        return session_id
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session_key = f"session:{session_id}:user:{user_id}"
        session_data = self.redis_client.get(session_key)
        
        if session_data:
            data = json.loads(session_data)
            # Update last accessed
            data["last_accessed"] = datetime.utcnow().isoformat()
            self.redis_client.setex(session_key, self.session_ttl, json.dumps(data))
            return data
        
        return None
    
    async def invalidate_session(self, session_id: str, user_id: str) -> bool:
        """Invalidate a specific session"""
        session_key = f"session:{session_id}:user:{user_id}"
        return bool(self.redis_client.delete(session_key))
    
    async def invalidate_all_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        session_keys = self.redis_client.keys(f"session:*:user:{user_id}")
        if session_keys:
            return self.redis_client.delete(*session_keys)
        return 0
    
    async def store_chat_session(self, session_id: str, user_id: str, chat_data: Dict[str, Any]):
        """Store chat session data"""
        chat_key = f"chat:{session_id}:user:{user_id}"
        self.redis_client.setex(chat_key, self.session_ttl, json.dumps(chat_data))
    
    async def get_chat_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session data"""
        chat_key = f"chat:{session_id}:user:{user_id}"
        chat_data = self.redis_client.get(chat_key)
        return json.loads(chat_data) if chat_data else None
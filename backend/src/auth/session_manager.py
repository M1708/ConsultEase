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
            print("Warning: REDIS_URL not found. Using mock session manager for tests.")
            self.redis_client = None
        else:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                print(f"Warning: Failed to connect to Redis: {e}. Using mock session manager.")
                self.redis_client = None
        self.session_ttl = int(os.getenv("SESSION_TTL", "86400"))  # 24 hours
        
        # Mock storage for testing
        self._mock_sessions = {}
        self._mock_chats = {}
        
    async def get_or_create_session(
        self, 
        user_id: str, 
        auth_user_id: str,  # Same value as user_id, but keeping for API compatibility
        email: str, 
        role: str
    ) -> str:
        """Get existing session or create new one"""
        if not self.redis_client:
            # Mock implementation for tests
            for session_id, data in self._mock_sessions.items():
                if data['user_id'] == user_id:
                    return session_id
            
            # Create new mock session
            session_id = str(uuid.uuid4())
            self._mock_sessions[session_id] = {
                "session_id": session_id,
                "user_id": user_id,
                "email": email,
                "role": role,
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat()
            }
            return session_id
        
        # Redis implementation
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
        if not self.redis_client:
            # Mock implementation
            data = self._mock_sessions.get(session_id)
            if data and data['user_id'] == user_id:
                data["last_accessed"] = datetime.utcnow().isoformat()
                return data
            return None
        
        # Redis implementation
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
        if not self.redis_client:
            # Mock implementation
            if session_id in self._mock_sessions:
                del self._mock_sessions[session_id]
                return True
            return False
        
        # Redis implementation
        session_key = f"session:{session_id}:user:{user_id}"
        return bool(self.redis_client.delete(session_key))
    
    async def invalidate_all_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        if not self.redis_client:
            # Mock implementation
            count = 0
            sessions_to_delete = []
            for session_id, data in self._mock_sessions.items():
                if data['user_id'] == user_id:
                    sessions_to_delete.append(session_id)
            
            for session_id in sessions_to_delete:
                del self._mock_sessions[session_id]
                count += 1
            return count
        
        # Redis implementation
        session_keys = self.redis_client.keys(f"session:*:user:{user_id}")
        if session_keys:
            return self.redis_client.delete(*session_keys)
        return 0
    
    async def store_chat_session(self, session_id: str, user_id: str, chat_data: Dict[str, Any]):
        """Store chat session data"""
        if not self.redis_client:
            # Mock implementation
            chat_key = f"chat:{session_id}:user:{user_id}"
            self._mock_chats[chat_key] = chat_data
            return
        
        # Redis implementation
        chat_key = f"chat:{session_id}:user:{user_id}"
        self.redis_client.setex(chat_key, self.session_ttl, json.dumps(chat_data))
    
    async def get_chat_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session data"""
        if not self.redis_client:
            # Mock implementation
            chat_key = f"chat:{session_id}:user:{user_id}"
            return self._mock_chats.get(chat_key)
        
        # Redis implementation
        chat_key = f"chat:{session_id}:user:{user_id}"
        chat_data = self.redis_client.get(chat_key)
        return json.loads(chat_data) if chat_data else None

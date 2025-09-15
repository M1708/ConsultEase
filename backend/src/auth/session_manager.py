import redis
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

class SessionManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
        return cls._instance
    def __init__(self):
        # Only initialize once
        if self._initialized:
            return
            
        redis_url = os.getenv("REDIS_URL")
        self.redis_available = False
        self.redis_client = None
        
        if not redis_url:
            print("Warning: REDIS_URL not found. Using in-memory session manager.")
        else:
            try:
                # Optimize Redis connection for better performance
                self.redis_client = redis.from_url(
                    redis_url, 
                    decode_responses=True,
                    socket_connect_timeout=2,  # 2s connection timeout
                    socket_timeout=2,          # 2s socket timeout
                    retry_on_timeout=True,     # Retry on timeout
                    health_check_interval=30,  # Health check every 30s
                    max_connections=10         # Limit connections
                )
                # Test connection
                self.redis_client.ping()
                self.redis_available = True
                print("Redis session manager initialized successfully.")
            except Exception as e:
                print(f"Warning: Failed to connect to Redis: {e}. Using in-memory session manager.")
                self.redis_client = None
                self.redis_available = False
                
        self.session_ttl = int(os.getenv("SESSION_TTL", "86400"))  # 24 hours
        
        # In-memory storage for fallback
        self._mock_sessions = {}
        self._mock_chats = {}
        
        # Mark as initialized
        self._initialized = True
        
    async def get_or_create_session(
        self, 
        user_id: str, 
        auth_user_id: str,  # Same value as user_id, but keeping for API compatibility
        email: str, 
        role: str
    ) -> str:
        """Get existing session or create new one"""
        if not self.redis_available or not self.redis_client:
            # In-memory implementation for fallback
            for session_id, data in self._mock_sessions.items():
                if data['user_id'] == user_id:
                    # Update last accessed
                    data['last_accessed'] = datetime.utcnow().isoformat()
                    return session_id
            
            # Create new in-memory session
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
        
        try:
            # Redis implementation with error handling
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
            
        except Exception as e:
            print(f"Redis error, falling back to in-memory: {e}")
            # Fallback to in-memory storage
            self.redis_available = False
            return await self.get_or_create_session(user_id, auth_user_id, email, role)
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        if not self.redis_available or not self.redis_client:
            # In-memory implementation
            data = self._mock_sessions.get(session_id)
            if data and data['user_id'] == user_id:
                data["last_accessed"] = datetime.utcnow().isoformat()
                return data
            return None
        
        try:
            # Redis implementation with error handling
            session_key = f"session:{session_id}:user:{user_id}"
            session_data = self.redis_client.get(session_key)
            
            if session_data:
                data = json.loads(session_data)
                # Update last accessed
                data["last_accessed"] = datetime.utcnow().isoformat()
                self.redis_client.setex(session_key, self.session_ttl, json.dumps(data))
                return data
            
            return None
            
        except Exception as e:
            print(f"Redis error in get_session, falling back to in-memory: {e}")
            self.redis_available = False
            data = self._mock_sessions.get(session_id)
            if data and data['user_id'] == user_id:
                data["last_accessed"] = datetime.utcnow().isoformat()
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
        print(f"🔍 DEBUG: store_chat_session called with session_id={session_id}, user_id={user_id}")
        print(f"🔍 DEBUG: Redis available: {self.redis_available}, Redis client: {self.redis_client is not None}")
        print(f"🔍 DEBUG: Chat data to store: {chat_data}")
        
        if not self.redis_client:
            # Mock implementation
            chat_key = f"chat:{session_id}:user:{user_id}"
            print(f"🔍 DEBUG: Using mock implementation, chat_key: {chat_key}")
            self._mock_chats[chat_key] = chat_data
            print(f"🔍 DEBUG: Mock storage complete")
            return
        
        # Redis implementation
        chat_key = f"chat:{session_id}:user:{user_id}"
        print(f"🔍 DEBUG: Redis implementation, chat_key: {chat_key}")
        try:
            self.redis_client.setex(chat_key, self.session_ttl, json.dumps(chat_data))
            print(f"🔍 DEBUG: Redis storage complete")
        except Exception as e:
            print(f"🔍 DEBUG: Redis error in store_chat_session: {e}")
    
    async def get_chat_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session data"""
        print(f"🔍 DEBUG: get_chat_session called with session_id={session_id}, user_id={user_id}")
        print(f"🔍 DEBUG: Redis available: {self.redis_available}, Redis client: {self.redis_client is not None}")
        
        if not self.redis_client:
            # Mock implementation
            chat_key = f"chat:{session_id}:user:{user_id}"
            print(f"🔍 DEBUG: Using mock implementation, chat_key: {chat_key}")
            result = self._mock_chats.get(chat_key)
            print(f"🔍 DEBUG: Mock result: {result}")
            return result
        
        # Redis implementation
        chat_key = f"chat:{session_id}:user:{user_id}"
        print(f"🔍 DEBUG: Redis implementation, chat_key: {chat_key}")
        try:
            chat_data = self.redis_client.get(chat_key)
            print(f"🔍 DEBUG: Raw Redis data: {chat_data}")
            if chat_data:
                data = json.loads(chat_data)
                print(f"🔍 DEBUG: Parsed Redis data: {data}")
                return data
            else:
                print(f"🔍 DEBUG: No data found in Redis for key: {chat_key}")
                return None
        except Exception as e:
            print(f"🔍 DEBUG: Redis error in get_chat_session: {e}")
            return None

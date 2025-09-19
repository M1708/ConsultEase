"""
Conversation memory manager that integrates with existing Redis session management.
Provides persistent memory for agent conversations and context.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.auth.session_manager import SessionManager
from ..graph.state import AgentState, AgentMemory


class ConversationMemoryManager:
    """Manages conversation memory using existing Redis infrastructure"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.memory_ttl = 7 * 24 * 3600  # 7 days for conversation memory
    
    async def store_conversation_memory(
        self, 
        session_id: str, 
        user_id: str, 
        memory: AgentMemory
    ) -> bool:
        """Store conversation memory in Redis"""
        try:
            memory_key = f"agent_memory:{session_id}:user:{user_id}"
            memory_data = {
                "conversation_history": memory["conversation_history"],
                "user_preferences": memory["user_preferences"],
                "context_summary": memory["context_summary"],
                "previous_tasks": memory["previous_tasks"],
                "learned_patterns": memory["learned_patterns"],
                "updated_at": datetime.now().isoformat()
            }
            
            self.session_manager.redis_client.setex(
                memory_key,
                self.memory_ttl,
                json.dumps(memory_data)
            )
            return True
        except Exception as e:
            print(f"Error storing conversation memory: {e}")
            return False
    
    async def retrieve_conversation_memory(
        self, 
        session_id: str, 
        user_id: str
    ) -> Optional[AgentMemory]:
        """Retrieve conversation memory from Redis"""
        try:
            memory_key = f"agent_memory:{session_id}:user:{user_id}"
            memory_data = self.session_manager.redis_client.get(memory_key)
            
            if memory_data:
                data = json.loads(memory_data)
                return AgentMemory(
                    conversation_history=data.get("conversation_history", []),
                    user_preferences=data.get("user_preferences", {}),
                    context_summary=data.get("context_summary", ""),
                    previous_tasks=data.get("previous_tasks", []),
                    learned_patterns=data.get("learned_patterns", {})
                )
            return None
        except Exception as e:
            print(f"Error retrieving conversation memory: {e}")
            return None
    
    async def update_conversation_history(
        self, 
        session_id: str, 
        user_id: str, 
        message: Dict[str, Any]
    ) -> bool:
        """Add a new message to conversation history"""
        try:
            memory = await self.retrieve_conversation_memory(session_id, user_id)
            if memory is None:
                memory = AgentMemory(
                    conversation_history=[],
                    user_preferences={},
                    context_summary="",
                    previous_tasks=[],
                    learned_patterns={}
                )
            
            # Add timestamp to message
            message["timestamp"] = datetime.now().isoformat()
            memory["conversation_history"].append(message)
            
            # Keep only last 50 messages to prevent memory bloat
            if len(memory["conversation_history"]) > 50:
                memory["conversation_history"] = memory["conversation_history"][-50:]
            
            return await self.store_conversation_memory(session_id, user_id, memory)
        except Exception as e:
            print(f"Error updating conversation history: {e}")
            return False
    
    async def update_user_preferences(
        self, 
        session_id: str, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> bool:
        """Update user preferences in memory"""
        try:
            memory = await self.retrieve_conversation_memory(session_id, user_id)
            if memory is None:
                memory = AgentMemory(
                    conversation_history=[],
                    user_preferences={},
                    context_summary="",
                    previous_tasks=[],
                    learned_patterns={}
                )
            
            memory["user_preferences"].update(preferences)
            return await self.store_conversation_memory(session_id, user_id, memory)
        except Exception as e:
            print(f"Error updating user preferences: {e}")
            return False
    
    async def update_context_summary(
        self, 
        session_id: str, 
        user_id: str, 
        summary: str
    ) -> bool:
        """Update context summary in memory"""
        try:
            memory = await self.retrieve_conversation_memory(session_id, user_id)
            if memory is None:
                memory = AgentMemory(
                    conversation_history=[],
                    user_preferences={},
                    context_summary="",
                    previous_tasks=[],
                    learned_patterns={}
                )
            
            memory["context_summary"] = summary
            return await self.store_conversation_memory(session_id, user_id, memory)
        except Exception as e:
            print(f"Error updating context summary: {e}")
            return False
    
    async def add_completed_task(
        self, 
        session_id: str, 
        user_id: str, 
        task: Dict[str, Any]
    ) -> bool:
        """Add a completed task to memory"""
        try:
            memory = await self.retrieve_conversation_memory(session_id, user_id)
            if memory is None:
                memory = AgentMemory(
                    conversation_history=[],
                    user_preferences={},
                    context_summary="",
                    previous_tasks=[],
                    learned_patterns={}
                )
            
            task["completed_at"] = datetime.now().isoformat()
            memory["previous_tasks"].append(task)
            
            # Keep only last 20 tasks
            if len(memory["previous_tasks"]) > 20:
                memory["previous_tasks"] = memory["previous_tasks"][-20:]
            
            return await self.store_conversation_memory(session_id, user_id, memory)
        except Exception as e:
            print(f"Error adding completed task: {e}")
            return False
    
    async def get_recent_context(
        self, 
        session_id: str, 
        user_id: str, 
        message_count: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent conversation context for agent processing"""
        try:
            memory = await self.retrieve_conversation_memory(session_id, user_id)
            if memory and memory["conversation_history"]:
                return memory["conversation_history"][-message_count:]
            return []
        except Exception as e:
            print(f"Error getting recent context: {e}")
            return []
    
    async def get_user_preferences_summary(
        self, 
        session_id: str, 
        user_id: str
    ) -> str:
        """Get a summary of user preferences for agent context"""
        try:
            memory = await self.retrieve_conversation_memory(session_id, user_id)
            if memory and memory["user_preferences"]:
                prefs = memory["user_preferences"]
                summary_parts = []
                
                for key, value in prefs.items():
                    summary_parts.append(f"{key}: {value}")
                
                return "User preferences: " + ", ".join(summary_parts)
            return "No user preferences recorded."
        except Exception as e:
            print(f"Error getting user preferences summary: {e}")
            return "Error retrieving user preferences."
    
    async def clear_conversation_memory(
        self, 
        session_id: str, 
        user_id: str
    ) -> bool:
        """Clear conversation memory for a session"""
        try:
            memory_key = f"agent_memory:{session_id}:user:{user_id}"
            return bool(self.session_manager.redis_client.delete(memory_key))
        except Exception as e:
            print(f"Error clearing conversation memory: {e}")
            return False

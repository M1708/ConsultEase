"""
Redis-based Memory Store for OpenAI Agents SDK

This module provides a dedicated memory store for OpenAI Agents SDK
that integrates with the existing Redis infrastructure while providing
SDK-specific memory management capabilities.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from ..memory.conversation_memory import ConversationMemoryManager
from ..memory.context_manager import ContextManager
from src.auth.session_manager import SessionManager


@dataclass
class AgentMemoryEntry:
    """Structured memory entry for SDK agents"""
    agent_id: str
    session_id: str
    user_id: str
    memory_type: str  # 'conversation', 'context', 'task', 'preference'
    content: Dict[str, Any]
    timestamp: str
    ttl: int = 7 * 24 * 3600  # 7 days default
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConversationContext:
    """SDK-specific conversation context"""
    session_id: str
    user_id: str
    agent_id: str
    recent_messages: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    context_summary: str
    active_tasks: List[Dict[str, Any]]
    last_updated: str


class SDKMemoryStore:
    """Memory store specifically designed for OpenAI Agents SDK integration"""

    def __init__(self):
        self.session_manager = SessionManager()
        self.existing_memory = ConversationMemoryManager()
        self.existing_context = ContextManager()
        self.default_ttl = 7 * 24 * 3600  # 7 days

    async def store_agent_memory(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        memory_data: Dict[str, Any],
        memory_type: str = "conversation"
    ) -> bool:
        """Store agent-specific memory in Redis"""
        try:
            memory_entry = AgentMemoryEntry(
                agent_id=agent_id,
                session_id=session_id,
                user_id=user_id,
                memory_type=memory_type,
                content=memory_data,
                timestamp=datetime.now().isoformat(),
                metadata={"source": "sdk_agent"}
            )

            # Create composite key for SDK memory
            memory_key = f"sdk_memory:{agent_id}:{session_id}:{user_id}:{memory_type}"

            # Check if Redis is available
            if self.session_manager.redis_client and self.session_manager.redis_available:
                # Store in Redis
                self.session_manager.redis_client.setex(
                    memory_key,
                    memory_entry.ttl,
                    json.dumps(asdict(memory_entry))
                )
            else:
                # Fallback to in-memory storage
                if not hasattr(self.session_manager, '_mock_sdk_memory'):
                    self.session_manager._mock_sdk_memory = {}
                self.session_manager._mock_sdk_memory[memory_key] = asdict(memory_entry)

            # Also update existing memory system for consistency
            await self._sync_with_existing_memory(agent_id, session_id, user_id, memory_data, memory_type)

            return True
        except Exception as e:
            print(f"Error storing SDK agent memory: {e}")
            return False

    async def retrieve_agent_memory(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        memory_type: str = "conversation"
    ) -> Optional[Dict[str, Any]]:
        """Retrieve agent-specific memory from Redis"""
        try:
            memory_key = f"sdk_memory:{agent_id}:{session_id}:{user_id}:{memory_type}"

            # Check if Redis is available
            if self.session_manager.redis_client and self.session_manager.redis_available:
                memory_data = self.session_manager.redis_client.get(memory_key)
                if memory_data:
                    entry_dict = json.loads(memory_data)
                    return entry_dict.get("content", {})
            else:
                # Check in-memory fallback
                if hasattr(self.session_manager, '_mock_sdk_memory'):
                    memory_data = self.session_manager._mock_sdk_memory.get(memory_key)
                    if memory_data:
                        return memory_data.get("content", {})

            # Fall back to existing memory system
            return await self._get_from_existing_memory(agent_id, session_id, user_id, memory_type)

        except Exception as e:
            print(f"Error retrieving SDK agent memory: {e}")
            return None

    async def update_conversation_context(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        context_updates: Dict[str, Any]
    ) -> bool:
        """Update conversation context for SDK agent"""
        try:
            # Get existing context
            existing_context = await self.retrieve_agent_memory(
                agent_id, session_id, user_id, "context"
            )

            if existing_context is None:
                existing_context = {}

            # Update context
            existing_context.update(context_updates)
            existing_context["last_updated"] = datetime.now().isoformat()

            # Store updated context
            return await self.store_agent_memory(
                agent_id, session_id, user_id, existing_context, "context"
            )

        except Exception as e:
            print(f"Error updating conversation context: {e}")
            return False

    async def store_conversation_history(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        messages: List[Dict[str, Any]],
        max_messages: int = 50
    ) -> bool:
        """Store conversation history for SDK agent"""
        try:
            # Get existing history
            existing_history = await self.retrieve_agent_memory(
                agent_id, session_id, user_id, "conversation"
            )

            if existing_history is None:
                existing_history = {"messages": []}

            if "messages" not in existing_history:
                existing_history["messages"] = []

            # Add new messages with timestamps
            for message in messages:
                if "timestamp" not in message:
                    message["timestamp"] = datetime.now().isoformat()
                message["agent_id"] = agent_id
                existing_history["messages"].append(message)

            # Keep only recent messages
            existing_history["messages"] = existing_history["messages"][-max_messages:]

            # Store updated history
            return await self.store_agent_memory(
                agent_id, session_id, user_id, existing_history, "conversation"
            )

        except Exception as e:
            print(f"Error storing conversation history: {e}")
            return False

    async def get_conversation_history(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent conversation history for SDK agent"""
        try:
            history_data = await self.retrieve_agent_memory(
                agent_id, session_id, user_id, "conversation"
            )

            if history_data and "messages" in history_data:
                return history_data["messages"][-limit:]
            return []

        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []

    async def store_agent_task(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        task_data: Dict[str, Any]
    ) -> bool:
        """Store task information for SDK agent"""
        try:
            task_data["created_at"] = datetime.now().isoformat()
            task_data["agent_id"] = agent_id

            return await self.store_agent_memory(
                agent_id, session_id, user_id, task_data, "task"
            )

        except Exception as e:
            print(f"Error storing agent task: {e}")
            return False

    async def get_agent_tasks(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get tasks for SDK agent"""
        try:
            tasks_data = await self.retrieve_agent_memory(
                agent_id, session_id, user_id, "task"
            )

            if tasks_data:
                tasks = [tasks_data] if isinstance(tasks_data, dict) else tasks_data

                if status:
                    return [task for task in tasks if task.get("status") == status]
                return tasks

            return []

        except Exception as e:
            print(f"Error getting agent tasks: {e}")
            return []

    async def update_user_preferences(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update user preferences for SDK agent"""
        try:
            # Get existing preferences
            existing_prefs = await self.retrieve_agent_memory(
                agent_id, session_id, user_id, "preferences"
            )

            if existing_prefs is None:
                existing_prefs = {}

            # Update preferences
            existing_prefs.update(preferences)
            existing_prefs["last_updated"] = datetime.now().isoformat()

            # Store updated preferences
            return await self.store_agent_memory(
                agent_id, session_id, user_id, existing_prefs, "preferences"
            )

        except Exception as e:
            print(f"Error updating user preferences: {e}")
            return False

    async def get_user_preferences(
        self,
        agent_id: str,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user preferences for SDK agent"""
        try:
            prefs = await self.retrieve_agent_memory(
                agent_id, session_id, user_id, "preferences"
            )

            return prefs if prefs else {}

        except Exception as e:
            print(f"Error getting user preferences: {e}")
            return {}

    async def clear_agent_memory(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        memory_type: Optional[str] = None
    ) -> bool:
        """Clear agent memory"""
        try:
            if memory_type:
                # Clear specific memory type
                memory_key = f"sdk_memory:{agent_id}:{session_id}:{user_id}:{memory_type}"
                return bool(self.session_manager.redis_client.delete(memory_key))
            else:
                # Clear all memory types for this agent
                pattern = f"sdk_memory:{agent_id}:{session_id}:{user_id}:*"
                keys = self.session_manager.redis_client.keys(pattern)
                if keys:
                    return bool(self.session_manager.redis_client.delete(*keys))
                return True

        except Exception as e:
            print(f"Error clearing agent memory: {e}")
            return False

    async def get_memory_stats(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            # Build pattern for keys
            pattern_parts = ["sdk_memory"]
            if agent_id:
                pattern_parts.append(agent_id)
            else:
                pattern_parts.append("*")

            if session_id:
                pattern_parts.append(session_id)
            else:
                pattern_parts.append("*")

            if user_id:
                pattern_parts.append(user_id)
            else:
                pattern_parts.append("*")

            pattern_parts.append("*")  # memory_type
            pattern = ":".join(pattern_parts)

            keys = self.session_manager.redis_client.keys(pattern)

            stats = {
                "total_keys": len(keys),
                "memory_types": {},
                "agents": set(),
                "sessions": set(),
                "users": set()
            }

            for key in keys:
                parts = key.split(":")
                if len(parts) >= 5:
                    agent = parts[1]
                    session = parts[2]
                    user = parts[3]
                    mem_type = parts[4]

                    stats["agents"].add(agent)
                    stats["sessions"].add(session)
                    stats["users"].add(user)

                    if mem_type not in stats["memory_types"]:
                        stats["memory_types"][mem_type] = 0
                    stats["memory_types"][mem_type] += 1

            # Convert sets to lists for JSON serialization
            stats["agents"] = list(stats["agents"])
            stats["sessions"] = list(stats["sessions"])
            stats["users"] = list(stats["users"])

            return stats

        except Exception as e:
            print(f"Error getting memory stats: {e}")
            return {"error": str(e)}

    async def _sync_with_existing_memory(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        memory_data: Dict[str, Any],
        memory_type: str
    ) -> None:
        """Sync SDK memory with existing memory system"""
        try:
            if memory_type == "conversation" and "messages" in memory_data:
                # Sync conversation history
                for message in memory_data["messages"][-5:]:  # Last 5 messages
                    await self.existing_memory.update_conversation_history(
                        session_id, user_id, message
                    )

            elif memory_type == "context":
                # Sync context summary
                if "context_summary" in memory_data:
                    await self.existing_memory.update_context_summary(
                        session_id, user_id, memory_data["context_summary"]
                    )

            elif memory_type == "preferences":
                # Sync user preferences
                await self.existing_memory.update_user_preferences(
                    session_id, user_id, memory_data
                )

        except Exception as e:
            print(f"Warning: Failed to sync with existing memory: {e}")

    async def _get_from_existing_memory(
        self,
        agent_id: str,
        session_id: str,
        user_id: str,
        memory_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get data from existing memory system as fallback"""
        try:
            if memory_type == "conversation":
                messages = await self.existing_memory.get_recent_context(
                    session_id, user_id, message_count=20
                )
                return {"messages": messages} if messages else None

            elif memory_type == "context":
                # Get context summary from existing system
                # This is a simplified fallback
                return {"context_summary": "Retrieved from existing memory"}

            elif memory_type == "preferences":
                prefs_summary = await self.existing_memory.get_user_preferences_summary(
                    session_id, user_id
                )
                return {"summary": prefs_summary} if prefs_summary else None

        except Exception as e:
            print(f"Warning: Failed to get from existing memory: {e}")
            return None

        return None

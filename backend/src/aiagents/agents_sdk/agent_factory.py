"""
Agent Factory for OpenAI Agents SDK Integration

This module provides factory methods for creating OpenAI Agents SDK agents
that integrate with the existing LangGraph workflow and memory systems.
"""

import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

# Import existing memory and context management
from ..memory.context_manager import ContextManager
from ..memory.conversation_memory import ConversationMemoryManager
from .memory_store import SDKMemoryStore
from ..graph.state import AgentState


class AgentFactory:
    """Factory for creating OpenAI Agents SDK compatible agents"""

    def __init__(self):
        self.context_manager = ContextManager()
        self.memory_manager = ConversationMemoryManager()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    def is_sdk_available(self) -> bool:
        """Check if OpenAI Agents SDK is available"""
        try:
            import openai
            return self.openai_api_key is not None
        except ImportError:
            return False

    def create_sdk_agent(
        self,
        agent_name: str,
        instructions: str,
        tools: Optional[List[Callable]] = None,
        model: str = "gpt-4o-mini"
    ) -> Optional[Any]:
        """Create an OpenAI Agents SDK agent"""
        if not self.is_sdk_available():
            print(f"OpenAI Agents SDK not available for agent {agent_name}")
            return None

        try:
            from agents import Agent

            agent = Agent(
                name=agent_name,
                instructions=instructions,
                tools=tools or [],
                model=model,
                model_settings={
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )
            return agent
        except Exception as e:
            print(f"Error creating SDK agent {agent_name}: {e}")
            return None

    def create_hybrid_agent(
        self,
        agent_name: str,
        instructions: str,
        tools: Optional[List[Callable]] = None,
        fallback_agent: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Create a hybrid agent that can use SDK or fallback to LangGraph"""
        sdk_agent = self.create_sdk_agent(agent_name, instructions, tools)

        return {
            "name": agent_name,
            "sdk_agent": sdk_agent,
            "fallback_agent": fallback_agent,
            "instructions": instructions,
            "tools": tools or [],
            "created_at": datetime.now().isoformat()
        }

    async def get_agent_context(
        self,
        agent_name: str,
        session_id: str,
        user_id: str
    ) -> str:
        """Get context for agent from existing memory system"""
        try:
            # Get conversation history
            recent_messages = await self.memory_manager.get_recent_context(
                session_id, user_id, message_count=10
            )

            # Get user preferences
            user_prefs = await self.memory_manager.get_user_preferences_summary(
                session_id, user_id
            )

            # Build context
            context_parts = []

            if user_prefs:
                context_parts.append(f"User Context: {user_prefs}")

            if recent_messages:
                message_summaries = []
                for msg in recent_messages[-5:]:  # Last 5 messages
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:200]  # First 200 chars
                    message_summaries.append(f"{role}: {content}")

                context_parts.append(f"Recent Conversation:\n" + "\n".join(message_summaries))

            return "\n\n".join(context_parts) if context_parts else "No previous context available."

        except Exception as e:
            print(f"Error getting agent context: {e}")
            return "Context retrieval failed."

    async def update_agent_memory(
        self,
        agent_name: str,
        session_id: str,
        user_id: str,
        interaction_data: Dict[str, Any]
    ) -> bool:
        """Update agent memory with interaction data"""
        try:
            # Store conversation history
            await self.memory_manager.update_conversation_history(
                session_id,
                user_id,
                {
                    "role": "assistant",
                    "content": interaction_data.get("response", ""),
                    "agent": agent_name,
                    "tools_used": interaction_data.get("tools_used", []),
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Update context summary if needed
            if interaction_data.get("significant_action"):
                summary = f"Agent {agent_name} performed: {interaction_data['significant_action']}"
                await self.memory_manager.update_context_summary(
                    session_id, user_id, summary
                )

            return True
        except Exception as e:
            print(f"Error updating agent memory: {e}")
            return False

    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """Get configuration for different agent types"""
        configs = {
            "contract_agent": {
                "instructions": """You are a contract management specialist. You help users with:
                - Creating new contracts for clients
                - Updating existing contract details
                - Searching and retrieving contract information
                - Managing contract documents
                - Tracking contract status and billing

                Always be precise with contract details and ask for clarification when needed.
                Use the available tools to perform contract operations.""",
                "model": "gpt-4o-mini",
                "tools": ["create_contract", "update_contract", "search_contracts", "get_contract_details"]
            },
            "client_agent": {
                "instructions": """You are a client relationship specialist. You help users with:
                - Creating and managing client profiles
                - Updating client contact information
                - Searching for existing clients
                - Managing client communications

                Be professional and maintain accurate client records.
                Use the available tools to perform client operations.""",
                "model": "gpt-4o-mini",
                "tools": ["create_client", "update_client", "search_clients", "get_client_details"]
            },
            "employee_agent": {
                "instructions": """You are an employee management specialist. You help users with:
                - Managing employee information
                - Tracking employee performance
                - Handling employee-related queries
                - Coordinating with HR processes

                Maintain confidentiality and accuracy in employee data.
                Use the available tools to perform employee operations.""",
                "model": "gpt-4o-mini",
                "tools": ["search_employees", "get_employee_details", "update_employee"]
            }
        }

        return configs.get(agent_type, {
            "instructions": "You are a helpful assistant.",
            "model": "gpt-4o-mini",
            "tools": []
        })

    async def create_agent_with_context(
        self,
        agent_type: str,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Create an agent with personalized context"""
        config = self.get_agent_config(agent_type)

        # Get personalized context
        context = await self.get_agent_context(agent_type, session_id, user_id)

        # Enhance instructions with context
        enhanced_instructions = f"{config['instructions']}\n\nContext:\n{context}"

        # Create hybrid agent
        agent = self.create_hybrid_agent(
            agent_name=agent_type,
            instructions=enhanced_instructions,
            tools=config.get('tools', [])
        )

        return agent

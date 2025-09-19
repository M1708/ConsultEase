"""
OpenAI Agents SDK Integration with LangGraph

This module provides the integration layer between OpenAI Agents SDK
and the existing LangGraph workflow system, enabling hybrid operation.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from ..agents_sdk.agent_factory import AgentFactory
from ..agents_sdk.tool_definitions import ToolRegistry
from ..agents_sdk.memory_store import SDKMemoryStore
from .state import AgentState
from ..memory.context_manager import ContextManager


class HybridAgentOrchestrator:
    """Orchestrator for hybrid SDK + LangGraph operation"""

    def __init__(self):
        self.agent_factory = AgentFactory()
        self.tool_registry = ToolRegistry()
        self.context_manager = ContextManager()
        self.sdk_agents = {}  # Cache for created SDK agents

    async def initialize_sdk_agents(self) -> bool:
        """Initialize OpenAI Agents SDK agents if available"""
        print(f"🔍 SDK INIT: Checking SDK availability...")
        
        if not self.agent_factory.is_sdk_available():
            print("🔍 SDK INIT: OpenAI Agents SDK not available, using fallback mode")
            return False

        try:
            # Initialize core agents
            agent_types = ["contract_agent", "client_agent", "employee_agent"]
            print(f"🔍 SDK INIT: Attempting to initialize {len(agent_types)} agent types")

            for agent_type in agent_types:
                print(f"🔍 SDK INIT: Creating agent '{agent_type}'...")
                agent = await self.agent_factory.create_agent_with_context(
                    agent_type=agent_type,
                    session_id="system_init",
                    user_id="system"
                )
                self.sdk_agents[agent_type] = agent
                print(f"🔍 SDK INIT: Agent '{agent_type}' created - has SDK agent: {agent.get('sdk_agent') is not None}")

            print(f"✅ Initialized {len(self.sdk_agents)} SDK agents")
            print(f"🔍 SDK INIT: Available agents: {list(self.sdk_agents.keys())}")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize SDK agents: {e}")
            import traceback
            print(f"🔍 SDK INIT: Full traceback: {traceback.format_exc()}")
            return False

    async def process_with_sdk_agent(
        self,
        agent_type: str,
        user_message: str,
        state: AgentState
    ) -> Optional[Dict[str, Any]]:
        """Process a user message using SDK agent if available"""
        if agent_type not in self.sdk_agents:
            print(f"🔍 SDK DEBUG: Agent type '{agent_type}' not in SDK agents: {list(self.sdk_agents.keys())}")
            return None

        try:
            sdk_agent = self.sdk_agents[agent_type].get("sdk_agent")
            if not sdk_agent:
                print(f"🔍 SDK DEBUG: No SDK agent found for '{agent_type}', attempting tool registry fallback")
                
                # Try to process with tool registry instead of placeholder response
                return await self._process_with_tool_registry(agent_type, user_message, state)

            print(f"🔍 SDK DEBUG: Using real SDK agent for '{agent_type}'")
            
            # Get agent context
            context = await self.agent_factory.get_agent_context(
                agent_type,
                state['context']['session_id'],
                state['context']['user_id']
            )

            # Process with actual SDK agent
            # TODO: Implement real OpenAI Agents SDK integration here
            response = {
                "agent": agent_type,
                "response": f"SDK Agent {agent_type} processed: {user_message}",
                "tools_used": [],
                "confidence": 0.8,
                "fallback_used": False
            }

            # Update agent memory
            await self.agent_factory.update_agent_memory(
                agent_type,
                state['context']['session_id'],
                state['context']['user_id'],
                {
                    "response": response["response"],
                    "tools_used": response["tools_used"],
                    "significant_action": "sdk_agent_response"
                }
            )

            return response

        except Exception as e:
            print(f"🔍 SDK DEBUG: Error processing with SDK agent {agent_type}: {e}")
            return None

    async def _process_with_tool_registry(
        self,
        agent_type: str,
        user_message: str,
        state: AgentState
    ) -> Optional[Dict[str, Any]]:
        """Fallback processing using our tool registry instead of placeholder"""
        print(f"🔍 SDK DEBUG: Using tool registry fallback for {agent_type}")
        
        # Instead of generic response, return None to let LangGraph handle it
        # This ensures we get proper tool execution instead of placeholder text
        return None

    async def process_with_fallback(
        self,
        agent_type: str,
        user_message: str,
        state: AgentState,
        fallback_function: Callable
    ) -> Dict[str, Any]:
        """Process using fallback LangGraph agent"""
        try:
            # Call the existing LangGraph agent function
            result = await fallback_function(state)

            response = {
                "agent": agent_type,
                "response": result.get("response", "Fallback processing completed"),
                "tools_used": result.get("tools_used", []),
                "confidence": 0.6,
                "fallback_used": True
            }

            return response

        except Exception as e:
            print(f"Error in fallback processing for {agent_type}: {e}")
            return {
                "agent": agent_type,
                "response": f"I apologize, but I'm having trouble processing your request about {user_message[:50]}...",
                "tools_used": [],
                "confidence": 0.0,
                "fallback_used": True,
                "error": str(e)
            }

    async def route_and_process(
        self,
        user_message: str,
        state: AgentState,
        agent_fallbacks: Dict[str, Callable]
    ) -> Dict[str, Any]:
        """Route message to appropriate agent and process"""

        # Determine which agent should handle this
        intent_data = self.context_manager.extract_user_intent(user_message)
        recommended_agent = self.context_manager.should_handoff_agent(
            state['current_agent'], intent_data, state
        )

        target_agent = recommended_agent or state['current_agent'] or 'contract_agent'

        # Try SDK agent first
        print(f"🔍 ROUTING DEBUG: Targeting agent '{target_agent}' for message: '{user_message[:50]}...'")
        sdk_response = await self.process_with_sdk_agent(target_agent, user_message, state)

        if sdk_response:
            return sdk_response

        # Fall back to LangGraph agent
        fallback_function = agent_fallbacks.get(target_agent)
        if fallback_function:
            return await self.process_with_fallback(
                target_agent, user_message, state, fallback_function
            )

        # Ultimate fallback
        return {
            "agent": "general_assistant",
            "response": f"I understand you want to {intent_data['primary_intent']} regarding {', '.join([e['value'] for e in intent_data['entities']])}. Let me help you with that.",
            "tools_used": [],
            "confidence": 0.4,
            "fallback_used": True
        }

    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "sdk_available": self.agent_factory.is_sdk_available(),
            "sdk_agents_initialized": len(self.sdk_agents) > 0,
            "available_agents": list(self.sdk_agents.keys()),
            "tool_count": len(self.tool_registry.get_tool_names()),
            "available_tools": self.tool_registry.get_tool_names()
        }


class HybridWorkflowNode:
    """LangGraph node that integrates SDK agents"""

    def __init__(self, orchestrator: HybridAgentOrchestrator):
        self.orchestrator = orchestrator

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Process state through hybrid workflow"""
        try:
            # Get the last user message
            last_message = state['messages'][-1] if state['messages'] else ""
            user_message = getattr(last_message, 'content', str(last_message))

            # Define fallback functions (these would be your existing agent functions)
            agent_fallbacks = {
                "contract_agent": self._contract_agent_fallback,
                "client_agent": self._client_agent_fallback,
                "employee_agent": self._employee_agent_fallback,
            }

            # Process through hybrid orchestrator
            result = await self.orchestrator.route_and_process(
                user_message, state, agent_fallbacks
            )

            # Update state with serializable message
            return {
                "messages": [{
                    "type": "ai",
                    "content": result["response"],
                    "role": "assistant"
                }],
                "current_agent": result["agent"],
                "data": {
                    **state.get("data", {}),
                    "tools_used": result["tools_used"],
                    "confidence": result["confidence"],
                    "fallback_used": result["fallback_used"]
                }
            }

        except Exception as e:
            print(f"Error in hybrid workflow node: {e}")
            return {"messages": [{
                "type": "ai",
                "content": "I apologize, but I'm experiencing technical difficulties. Please try again.",
                "role": "assistant"
            }]}

    async def _contract_agent_fallback(self, state: AgentState) -> Dict[str, Any]:
        """Fallback contract agent processing"""
        # This would call your existing contract agent logic
        return {
            "response": "Contract agent fallback: Processing contract-related request",
            "tools_used": [],
            "agent": "contract_agent"
        }

    async def _client_agent_fallback(self, state: AgentState) -> Dict[str, Any]:
        """Fallback client agent processing"""
        # This would call your existing client agent logic
        return {
            "response": "Client agent fallback: Processing client-related request",
            "tools_used": [],
            "agent": "client_agent"
        }

    async def _employee_agent_fallback(self, state: AgentState) -> Dict[str, Any]:
        """Fallback employee agent processing"""
        # This would call your existing employee agent logic
        return {
            "response": "Employee agent fallback: Processing employee-related request",
            "tools_used": [],
            "agent": "employee_agent"
        }


# Global orchestrator instance
hybrid_orchestrator = HybridAgentOrchestrator()

async def initialize_hybrid_system() -> bool:
    """Initialize the hybrid SDK + LangGraph system"""
    return await hybrid_orchestrator.initialize_sdk_agents()

def create_hybrid_workflow_node() -> HybridWorkflowNode:
    """Create a hybrid workflow node for LangGraph integration"""
    return HybridWorkflowNode(hybrid_orchestrator)

def get_hybrid_orchestrator() -> HybridAgentOrchestrator:
    """Get the global hybrid orchestrator instance"""
    return hybrid_orchestrator

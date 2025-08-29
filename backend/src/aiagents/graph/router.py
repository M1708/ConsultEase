import os
import json
from openai import OpenAI
from typing import Dict, List, Optional
from datetime import datetime

from .state import AgentState, update_state_for_handoff
from ..memory.context_manager import ContextManager


class IntelligentRouter:
    """Enhanced router using OpenAI function calling for intelligent agent selection"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            # For testing environments without API key
            self.client = None
            print("Warning: OpenAI API key not found. Router will use fallback mode.")
        self.model = model
        self.context_manager = ContextManager()
    
    def get_routing_functions(self) -> List[Dict]:
        """Define function schemas for OpenAI function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "route_to_agent",
                    "description": "Route the user's request to the most appropriate specialized agent based on their expertise",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "enum": [
                                    "client_agent",
                                    "contract_agent", 
                                    "employee_agent",
                                    "deliverable_agent",
                                    "time_agent",
                                    "user_agent"
                                ],
                                "description": "The specialized agent to handle this request"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Brief explanation of why this agent was selected"
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "Confidence level in the routing decision"
                            }
                        },
                        "required": ["agent_name", "reasoning", "confidence"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "handle_greeting",
                    "description": "Handle general greetings and casual conversation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "response_type": {
                                "type": "string",
                                "enum": ["greeting", "help", "capabilities"],
                                "description": "Type of greeting response needed"
                            }
                        },
                        "required": ["response_type"]
                    }
                }
            }
        ]
    
    async def call_llm_for_routing(self, user_message: str, state: AgentState) -> Dict:
        """Use OpenAI function calling to determine the best routing decision"""
        try:
            # If no OpenAI client available, use fallback routing
            if self.client is None:
                print("Using fallback routing (no OpenAI API key)")
                return self.fallback_routing(user_message)
            
            # Get enhanced context for routing decision
            context = await self.context_manager.get_enhanced_context(state, "router")
            
            # Build system prompt with context
            system_prompt = f"""You are an intelligent routing system for a consulting management application.

Your job is to analyze user requests and route them to the most appropriate specialized agent:

- client_agent: Handles client management, company information, contact details, client creation/updates
- contract_agent: Manages contracts, agreements, terms, renewals for EXISTING clients
- employee_agent: Handles employee/contractor management, HR tasks, staff onboarding
- deliverable_agent: Manages project deliverables, milestones, tasks, project tracking
- time_agent: Handles time tracking, timesheets, hour logging, productivity management
- user_agent: Manages user accounts, profiles, permissions, account settings

Current context:
{context}

Agent Specializations:
- client_agent: "create client", "search client", "update client", "client details", "company information"
- contract_agent: "create contract", "contract details", "agreement", "contract terms", "billing"
- employee_agent: "add employee", "staff management", "HR", "personnel", "hire", "employee details"
- deliverable_agent: "project deliverable", "milestone", "task management", "project status"
- time_agent: "log hours", "timesheet", "time entry", "track time", "productivity"
- user_agent: "user account", "profile", "permissions", "manage users", "account settings"

Consider:
1. The user's specific request and intent
2. Which agent specializes in the requested domain
3. The user's role and permissions
4. Previous conversation context

If the request is a simple greeting, use handle_greeting.
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.get_routing_functions(),
                tool_choice="auto",
                temperature=0.1
            )
            
            message = response.choices[0].message
            
            if message.tool_calls and len(message.tool_calls) > 0:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                return {
                    "function": function_name,
                    "arguments": function_args,
                    "reasoning": message.content or "Routing decision made"
                }
            else:
                # Fallback to content-based routing
                return {
                    "function": "route_to_agent",
                    "arguments": {
                        "agent_name": "client_agent",
                        "reasoning": "No clear routing decision, defaulting to client agent",
                        "confidence": "low"
                    }
                }
                
        except Exception as e:
            print(f"Error in LLM routing: {e}")
            # Fallback to simple keyword-based routing
            return self.fallback_routing(user_message)
    
    def fallback_routing(self, user_message: str) -> Dict:
        """Fallback keyword-based routing when LLM fails"""
        message_lower = user_message.lower()
        
        # Enhanced keyword matching with better logic
        # Check for update operations first (most specific)
        if any(word in message_lower for word in ["update", "modify", "change", "edit", "set"]):
            # Determine what entity is being updated
            if any(word in message_lower for word in ["client", "company", "customer", "contact", "person"]) and not any(word in message_lower for word in ["contract", "agreement"]):
                return {
                    "function": "route_to_agent",
                    "arguments": {
                        "agent_name": "client_agent",
                        "reasoning": "Client update operation detected",
                        "confidence": "high"
                    }
                }
            elif any(word in message_lower for word in ["contract", "agreement", "billing", "prompt", "date"]):
                return {
                    "function": "route_to_agent",
                    "arguments": {
                        "agent_name": "contract_agent",
                        "reasoning": "Contract update operation detected",
                        "confidence": "high"
                    }
                }
            else:
                # Check if it mentions a client name with update - likely contract update
                if any(client_name in message_lower for client_name in ["acme", "techcorp", "global retail"]):
                    return {
                        "function": "route_to_agent",
                        "arguments": {
                            "agent_name": "contract_agent",
                            "reasoning": "Update operation with client name detected - likely contract update",
                            "confidence": "high"
                        }
                    }
                # Default to client agent for general updates
                return {
                    "function": "route_to_agent",
                    "arguments": {
                        "agent_name": "client_agent",
                        "reasoning": "Update operation detected, defaulting to client agent",
                        "confidence": "medium"
                    }
                }
        
        # Check for contract-specific requests
        elif any(phrase in message_lower for phrase in [
            "all contracts", "show contracts", "list contracts", "contract details",
            "contracts for", "client contracts", "contract information"
        ]):
            return {
                "function": "route_to_agent", 
                "arguments": {
                    "agent_name": "contract_agent",
                    "reasoning": "Contract-specific request detected",
                    "confidence": "high"
                }
            }
        
        # Check for client with contracts requests
        elif any(phrase in message_lower for phrase in [
            "clients with contracts", "clients and contracts", "all clients with their contracts",
            "show me all clients with their contracts", "clients with their contracts"
        ]):
            return {
                "function": "route_to_agent",
                "arguments": {
                    "agent_name": "contract_agent",
                    "reasoning": "Client with contracts request - contract agent has the comprehensive tool",
                    "confidence": "high"
                }
            }
        
        # Check for general client requests (including contact person updates)
        elif any(word in message_lower for word in ["client", "company", "customer", "contact person", "contact"]) and not any(word in message_lower for word in ["contract"]):
            return {
                "function": "route_to_agent",
                "arguments": {
                    "agent_name": "client_agent",
                    "reasoning": "Client-related request detected",
                    "confidence": "high"
                }
            }
        
        # Check for contract requests
        elif any(word in message_lower for word in ["contract", "agreement"]):
            return {
                "function": "route_to_agent", 
                "arguments": {
                    "agent_name": "contract_agent",
                    "reasoning": "Contract-related request detected",
                    "confidence": "medium"
                }
            }
        elif any(word in message_lower for word in ["employee", "staff", "hire"]):
            return {
                "function": "route_to_agent",
                "arguments": {
                    "agent_name": "employee_agent", 
                    "reasoning": "Keyword match for employee-related request",
                    "confidence": "medium"
                }
            }
        elif any(word in message_lower for word in ["deliverable", "project", "milestone"]):
            return {
                "function": "route_to_agent",
                "arguments": {
                    "agent_name": "deliverable_agent",
                    "reasoning": "Keyword match for deliverable-related request",
                    "confidence": "medium"
                }
            }
        elif any(word in message_lower for word in ["time", "hours", "timesheet"]):
            return {
                "function": "route_to_agent",
                "arguments": {
                    "agent_name": "time_agent",
                    "reasoning": "Keyword match for time-related request", 
                    "confidence": "medium"
                }
            }
        elif any(word in message_lower for word in ["user", "account", "profile"]):
            return {
                "function": "route_to_agent",
                "arguments": {
                    "agent_name": "user_agent",
                    "reasoning": "Keyword match for user-related request",
                    "confidence": "medium"
                }
            }
        elif any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return {
                "function": "handle_greeting",
                "arguments": {
                    "response_type": "greeting"
                }
            }
        else:
            return {
                "function": "route_to_agent",
                "arguments": {
                    "agent_name": "client_agent",
                    "reasoning": "No clear match, defaulting to client agent",
                    "confidence": "low"
                }
            }


# Global router instance
intelligent_router = IntelligentRouter()


def master_router_node_sync(state: AgentState) -> Dict:
    """
    Synchronous version of the router for compatibility with sync tests.
    """
    try:
        # Get the last user message
        user_message = ""
        if state['messages'] and isinstance(state['messages'][-1], dict):
            user_message = state['messages'][-1].get('content', '')
        elif state['messages'] and hasattr(state['messages'][-1], 'content'):
            user_message = state['messages'][-1].content
        
        if not user_message:
            return {"current_agent": "client_agent"}
        
        # Use fallback routing for sync calls
        routing_decision = intelligent_router.fallback_routing(user_message)
        
        function_name = routing_decision["function"]
        arguments = routing_decision["arguments"]
        
        print(f"🧠 Sync Router: {arguments.get('reasoning', 'Routing decision made')}")
        
        if function_name == "route_to_agent":
            agent_name = arguments["agent_name"]
            reasoning = arguments["reasoning"]
            
            # Check if this is a handoff situation
            if state.get('current_agent') and state['current_agent'] != "router" and state['current_agent'] != agent_name:
                # Update state for handoff
                update_state_for_handoff(state, agent_name, reasoning)
                print(f"🔄 Agent Handoff: {state.get('previous_agent', 'unknown')} → {agent_name}")
            
            return {"current_agent": agent_name}
            
        elif function_name == "handle_greeting":
            return {"current_agent": "greeting"}
        
        else:
            return {"current_agent": "client_agent"}
            
    except Exception as e:
        print(f"Error in sync router: {e}")
        # Fallback to simple routing
        return {"current_agent": "client_agent"}


async def master_router_node(state: AgentState) -> Dict:
    """
    Enhanced router that uses OpenAI function calling for intelligent agent selection.
    Integrates with existing agent architecture and maintains compatibility.
    """
    try:
        # Get the last user message
        user_message = ""
        if state['messages'] and isinstance(state['messages'][-1], dict):
            user_message = state['messages'][-1].get('content', '')
        elif state['messages'] and hasattr(state['messages'][-1], 'content'):
            user_message = state['messages'][-1].content
        
        if not user_message:
            return {"current_agent": "client_agent"}
        
        # Get routing decision from LLM
        routing_decision = await intelligent_router.call_llm_for_routing(user_message, state)
        
        function_name = routing_decision["function"]
        arguments = routing_decision["arguments"]
        
        print(f"🧠 Intelligent Router: {arguments.get('reasoning', 'Routing decision made')}")
        
        if function_name == "route_to_agent":
            agent_name = arguments["agent_name"]
            reasoning = arguments["reasoning"]
            
            # Check if this is a handoff situation
            if state.get('current_agent') and state['current_agent'] != "router" and state['current_agent'] != agent_name:
                # Update state for handoff
                update_state_for_handoff(state, agent_name, reasoning)
                print(f"🔄 Agent Handoff: {state.get('previous_agent', 'unknown')} → {agent_name}")
            
            return {"current_agent": agent_name}
            
        elif function_name == "handle_greeting":
            return {"current_agent": "greeting"}
        
        else:
            return {"current_agent": "client_agent"}
            
    except Exception as e:
        print(f"Error in master router: {e}")
        # Fallback to simple routing
        return {"current_agent": "client_agent"}


# Hybrid router that works with both sync and async
def router(state: AgentState) -> Dict:
    """
    Hybrid router function that works with both sync and async calls.
    LangGraph will use this as the main router.
    """
    import asyncio
    
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, but LangGraph is calling us synchronously
            # Use the sync version
            return master_router_node_sync(state)
        else:
            # We can run async
            return asyncio.run(master_router_node(state))
    except RuntimeError:
        # No event loop, use sync version
        return master_router_node_sync(state)

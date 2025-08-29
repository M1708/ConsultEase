from typing import Dict, Any, List

from src.aiagents.memory.conversation_memory import ConversationMemoryManager
from src.aiagents.memory.context_manager import ContextManager

class ClientAgent:
    """
    Enhanced Client Agent with memory integration and context awareness.
    All runtime logic is handled by the LangGraph engine.
    """
    def __init__(self):
        """Initializes the agent with its specific instructions and tool schemas."""
        self.instructions = "You are Milo, an AI assistant."
        self.tools = self._get_tool_schemas()
        self.memory_manager = ConversationMemoryManager()
        self.context_manager = ContextManager()
    
    async def get_enhanced_instructions(self, state) -> str:
        """Get enhanced instructions with memory context"""
        try:
            # Get enhanced context for this agent
            context = await self.context_manager.get_enhanced_context(state, "client_agent")
            
            # Get user preferences summary
            preferences = await self.memory_manager.get_user_preferences_summary(
                state['context']['session_id'],
                state['context']['user_id']
            )
            
            # Enhance base instructions with context
            enhanced_instructions = f"""{self.instructions}

CURRENT CONTEXT:
{context}

{preferences}

MEMORY-ENHANCED BEHAVIOR:
- Consider the user's previous interactions and preferences
- Reference past client management activities when relevant
- Adapt your communication style based on user patterns
- Remember client details from previous conversations
"""
            
            return enhanced_instructions
            
        except Exception as e:
            print(f"Error getting enhanced instructions: {e}")
            return self.instructions

    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Defines the OpenAI function calling schemas for the tools this agent can use.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_client",
                    "description": "Create a new client record in the CRM system with company information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "The full name of the client company"},
                            "industry": {"type": "string", "description": "The industry the client operates in"},
                            "primary_contact_name": {"type": "string", "description": "Name of the primary contact"},
                            "primary_contact_email": {"type": "string", "description": "Email of the primary contact"},
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_clients",
                    "description": "Search for existing clients by name, industry, or other criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {"type": "string", "description": "Term to search for clients"}
                        },
                        "required": ["search_term"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_clients",
                    "description": "Get a list of all clients in the system (basic client information only).",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_clients_with_contracts",
                    "description": "Get a comprehensive list of all clients with their contract details. Use this when user asks for 'clients with contracts', 'clients and their contracts', or similar requests that need both client and contract information.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_client_details",
                    "description": "Get detailed information for a specific client.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "The name of the client"}
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_client",
                    "description": "Update an existing client's information like contact details, industry, notes, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "Name of the client to update"},
                            "industry": {"type": "string", "description": "New industry or business sector"},
                            "primary_contact_name": {"type": "string", "description": "New primary contact person name"},
                            "primary_contact_email": {"type": "string", "description": "New primary contact email address"},
                            "notes": {"type": "string", "description": "New notes or comments about the client"}
                        },
                        "required": ["client_name"]
                    }
                }
            }
        ]

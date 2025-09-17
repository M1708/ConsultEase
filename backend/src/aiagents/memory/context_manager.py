"""
Context manager that integrates with existing cache system.
Provides intelligent context management for agent conversations.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.aiagents.cache_manager import agent_cache, cached_query
from src.aiagents.graph.state import AgentState
from .conversation_memory import ConversationMemoryManager


class ContextManager:
    """Manages conversation context using existing cache infrastructure"""
    
    def __init__(self):
        self.memory_manager = ConversationMemoryManager()
        self.context_cache_ttl = 300  # 5 minutes for context cache
    
    def build_agent_context(
        self, 
        state: AgentState, 
        agent_name: str
    ) -> str:
        """Build context string for agent processing"""
        context_parts = []
        
        # Add user information
        user_context = f"User: {state['context']['user_name']} ({state['context']['user_role']})"
        context_parts.append(user_context)
        
        
        # Add conversation summary
        if state['memory']['context_summary']:
            context_parts.append(f"Context: {state['memory']['context_summary']}")
        
        # Add user preferences
        if state['memory']['user_preferences']:
            prefs = []
            for key, value in state['memory']['user_preferences'].items():
                prefs.append(f"{key}: {value}")
            if prefs:
                context_parts.append(f"User preferences: {', '.join(prefs)}")
        
        # Add recent tasks
        if state['memory']['previous_tasks']:
            recent_tasks = state['memory']['previous_tasks'][-3:]  # Last 3 tasks
            task_summaries = []
            for task in recent_tasks:
                task_summaries.append(f"- {task.get('description', 'Unknown task')}")
            if task_summaries:
                context_parts.append(f"Recent tasks:\n{chr(10).join(task_summaries)}")
        
        # Add agent handoff information
        if state['previous_agent'] and state['agent_handoff_reason']:
            handoff_context = f"Handed off from {state['previous_agent']} because: {state['agent_handoff_reason']}"
            context_parts.append(handoff_context)
        
        # Add collaboration information
        if state['collaboration_mode'] and len(state['active_agents']) > 1:
            other_agents = [a for a in state['active_agents'] if a != agent_name]
            if other_agents:
                context_parts.append(f"Collaborating with: {', '.join(other_agents)}")
        
        return "\n\n".join(context_parts)
    
    async def get_enhanced_context(
        self, 
        state: AgentState, 
        agent_name: str
    ) -> str:
        """Get enhanced context including memory and cache"""
        try:
            # Build cache key
            cache_key = f"context:{state['context']['session_id']}:{agent_name}"
            
            # Try to get from cache first
            cached_context = agent_cache.get(cache_key)
            if cached_context:
                return cached_context
            
            # Build fresh context
            context = self.build_agent_context(state, agent_name)
            
            # Get recent conversation history
            recent_messages = await self.memory_manager.get_recent_context(
                state['context']['session_id'],
                state['context']['user_id'],
                message_count=5
            )
            
            if recent_messages:
                message_summaries = []
                for msg in recent_messages:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:100]  # First 100 chars
                    message_summaries.append(f"{role}: {content}...")
                
                context += f"\n\nRecent conversation:\n{chr(10).join(message_summaries)}"
            
            # Cache the context
            agent_cache.set(cache_key, context)
            
            return context
            
        except Exception as e:
            print(f"Error getting enhanced context: {e}")
            return self.build_agent_context(state, agent_name)
    
    def extract_user_intent(self, message: str) -> Dict[str, Any]:
        """Extract user intent from message (enhanced with entity recognition)"""
        message_lower = message.lower()
        
        intent_data = {
            "primary_intent": "unknown",
            "entities": [],
            "urgency": "normal",
            "complexity": "simple",
            "referenced_entities": []  # Entities mentioned that might be from previous context
        }
        
        # Intent classification
        if any(word in message_lower for word in ["create", "add", "new"]):
            intent_data["primary_intent"] = "create"
        elif any(word in message_lower for word in ["update", "modify", "change", "edit"]):
            intent_data["primary_intent"] = "update"
        elif any(word in message_lower for word in ["delete", "remove", "cancel"]):
            intent_data["primary_intent"] = "delete"
        elif any(word in message_lower for word in ["search", "find", "look", "show", "list"]):
            intent_data["primary_intent"] = "retrieve"
        elif any(word in message_lower for word in ["help", "how", "what", "explain"]):
            intent_data["primary_intent"] = "help"
        
        # Entity extraction (enhanced with context references)
        entities = []
        referenced_entities = []
        
        if "client" in message_lower:
            entities.append({"type": "entity", "value": "client"})
        if "contract" in message_lower:
            entities.append({"type": "entity", "value": "contract"})
        if "employee" in message_lower:
            entities.append({"type": "entity", "value": "employee"})
        if "time" in message_lower or "hours" in message_lower:
            entities.append({"type": "entity", "value": "time_entry"})
        if "expense" in message_lower:
            entities.append({"type": "entity", "value": "expense"})
        
        # Check for contextual references (pronouns and demonstratives)
        if any(word in message_lower for word in ["it", "its", "this", "that", "them", "they"]):
            referenced_entities.append({"type": "reference", "value": "contextual_reference"})
        
        # Check for possessive references
        if any(phrase in message_lower for phrase in ["their contract", "its contract", "the contract"]):
            referenced_entities.append({"type": "reference", "value": "contract_reference"})
        
        intent_data["entities"] = entities
        intent_data["referenced_entities"] = referenced_entities
        
        # Urgency detection
        if any(word in message_lower for word in ["urgent", "asap", "immediately", "emergency"]):
            intent_data["urgency"] = "high"
        elif any(word in message_lower for word in ["when possible", "later", "eventually"]):
            intent_data["urgency"] = "low"
        
        # Complexity detection
        if any(word in message_lower for word in ["and", "also", "then", "after"]):
            intent_data["complexity"] = "complex"
        
        return intent_data
    
    def should_handoff_agent(
        self, 
        current_agent: str, 
        intent_data: Dict[str, Any], 
        state: AgentState
    ) -> Optional[str]:
        """Determine if agent handoff is needed based on intent"""
        primary_intent = intent_data["primary_intent"]
        entities = [e["value"] for e in intent_data["entities"]]
        
        # Agent specialization mapping
        agent_specializations = {
            "client_agent": ["client", "company", "customer"],
            "contract_agent": ["contract", "agreement", "deal"],
            "employee_agent": ["employee", "staff", "personnel"],
            "deliverable_agent": ["deliverable", "project", "milestone"],
            "time_agent": ["time_entry", "timesheet", "hours"],
            "user_agent": ["user", "account", "profile"]
        }
        
        # Find best agent for entities
        best_agent = None
        max_matches = 0
        
        for agent, specializations in agent_specializations.items():
            matches = len(set(entities) & set(specializations))
            if matches > max_matches and agent != current_agent:
                max_matches = matches
                best_agent = agent
        
        # Only handoff if we found a better match
        if best_agent and max_matches > 0:
            return best_agent
        
        return None
    
    async def update_context_from_interaction(
        self, 
        state: AgentState, 
        user_message: str, 
        agent_response: str
    ) -> AgentState:
        """Update context based on user interaction"""
        try:
            # Extract intent from user message
            intent_data = self.extract_user_intent(user_message)
            
            # Update conversation history
            await self.memory_manager.update_conversation_history(
                state['context']['session_id'],
                state['context']['user_id'],
                {
                    "role": "user",
                    "content": user_message,
                    "intent": intent_data
                }
            )
            
            await self.memory_manager.update_conversation_history(
                state['context']['session_id'],
                state['context']['user_id'],
                {
                    "role": "assistant",
                    "content": agent_response,
                    "agent": state['current_agent']
                }
            )
            
            # Update context summary if this is a significant interaction
            if intent_data["primary_intent"] in ["create", "update", "delete"]:
                summary = f"User performed {intent_data['primary_intent']} operation on {', '.join([e['value'] for e in intent_data['entities']])}"
                await self.memory_manager.update_context_summary(
                    state['context']['session_id'],
                    state['context']['user_id'],
                    summary
                )
            
            # Clear context cache to force refresh
            cache_key = f"context:{state['context']['session_id']}:{state['current_agent']}"
            agent_cache.cache.pop(cache_key, None)
            
            return state
            
        except Exception as e:
            print(f"Error updating context from interaction: {e}")
            return state
    
    def get_handoff_recommendation(
        self, 
        state: AgentState, 
        user_message: str
    ) -> Optional[Dict[str, str]]:
        """Get agent handoff recommendation"""
        try:
            intent_data = self.extract_user_intent(user_message)
            recommended_agent = self.should_handoff_agent(
                state['current_agent'], 
                intent_data, 
                state
            )
            
            if recommended_agent:
                entities = [e["value"] for e in intent_data["entities"]]
                reason = f"User intent '{intent_data['primary_intent']}' with entities {entities} better handled by {recommended_agent}"
                
                return {
                    "recommended_agent": recommended_agent,
                    "reason": reason,
                    "confidence": "high" if len(intent_data["entities"]) > 0 else "medium"
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting handoff recommendation: {e}")
            return None

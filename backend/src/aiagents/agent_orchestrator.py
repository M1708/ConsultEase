from typing import Dict, Any, List, Optional
from backend.src.aiagents.contract_agent import ContractAgent
from backend.src.aiagents.time_agent import TimeTrackerAgent
from backend.src.aiagents.deliverable_agent import DeliverableAgent
from backend.src.aiagents.employee_agent import EmployeeAgent
from backend.src.aiagents.workflows.client_onboarding_workflow import ClientOnboardingWorkflow
from backend.src.aiagents.workflows.base_workflow import WorkflowState, WorkflowStatus
import uuid
from datetime import datetime

class MultiAgentOrchestrator:
    def __init__(self):
        # Initialize agents
        self.agents = {
            "contract": ContractAgent(),
            "time": TimeTrackerAgent(),
            "deliverable": DeliverableAgent(),
            "employee": EmployeeAgent()
        }
        
        # Initialize workflows
        self.workflows = {
            "client_onboarding": ClientOnboardingWorkflow()
        }
        
        # Active workflow tracking
        self.active_workflows: Dict[str, WorkflowState] = {}
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for processing user messages"""
        print(f"🎯 AgentOrchestrator: Processing message: {message}")
        
        # Check if message is a greeting
        greeting_result = self._handle_greeting(message, context)
        if greeting_result:
            print(f"🎯 AgentOrchestrator: Greeting detected, returning personalized response")
            return greeting_result
        
        # Check if message is workflow-related
        workflow_result = await self._check_workflow_intent(message, context)
        if workflow_result:
            print(f"🎯 AgentOrchestrator: Workflow result returned: {workflow_result}")
            return workflow_result
        
        # Route to appropriate agent
        selected_agent = self._select_agent(message, context)
        print(f"🎯 AgentOrchestrator: Selected agent: {selected_agent.__class__.__name__ if selected_agent else 'None'}")
        
        if selected_agent:
            print(f"🎯 AgentOrchestrator: Calling agent.process_message")
            # Enhance context with conversation history for better persistence
            enhanced_context = self._enhance_context_with_history(context, message)
            result = await selected_agent.process_message(message, enhanced_context)
            print(f"🎯 AgentOrchestrator: Agent result: {result}")
            return result
        
        # Fallback response
        fallback_result = {
            "agent": "Milo",
            "response": "I can help you with client management, time tracking, and project coordination. How can I assist you today?",
            "success": True
        }
        print(f"🎯 AgentOrchestrator: Returning fallback result: {fallback_result}")
        return fallback_result
    
    def _handle_greeting(self, message: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle greeting messages with personalized responses"""
        message_lower = message.lower().strip()
        
        # Define greeting patterns - only exact matches or standalone greetings
        greeting_patterns = [
            "hello", "hi", "hey", "sup", "yo", "greetings"
        ]
        
        # Time-based greetings that should be more specific
        time_greetings = [
            "good morning", "good afternoon", "good evening", "morning", "afternoon", "evening"
        ]
        
        # Check if message is a standalone greeting (not part of a longer message)
        is_greeting = False
        
        # For time-based greetings, check if they're at the start of the message
        for time_greeting in time_greetings:
            if message_lower.startswith(time_greeting) and len(message_lower.strip()) <= len(time_greeting) + 5:
                is_greeting = True
                break
        
        # For simple greetings, check if they're the only content or very short
        if not is_greeting:
            for greeting in greeting_patterns:
                if message_lower == greeting or message_lower == f"{greeting}!" or message_lower == f"{greeting}.":
                    is_greeting = True
                    break
        
        # IMPORTANT: If the message contains business-related keywords, it's NOT a greeting
        business_keywords = [
            "create", "add", "new", "employee", "client", "contract", "deliverable", "time", "track", "update", "search", "find", "show", "list", "get", "manage"
        ]
        
        # If message contains business keywords, it's not a greeting
        if any(keyword in message_lower for keyword in business_keywords):
            is_greeting = False
        
        if not is_greeting:
            return None
        
        # Extract user's first name from context
        user_first_name = "User"  # Default fallback
        
        if context and "user_first_name" in context:
            user_first_name = context["user_first_name"]
        elif context and "user_name" in context:
            # Try to extract first name from full name
            full_name = context["user_name"]
            if full_name and " " in full_name:
                user_first_name = full_name.split(" ")[0]
            elif full_name:
                user_first_name = full_name
        
        # Create personalized greeting response
        greeting_response = f"Hello {user_first_name}! How can I help you today?"
        
        return {
            "agent": "Milo",
            "response": greeting_response,
            "success": True,
            "timestamp": context.get("timestamp", ""),
            "session_id": context.get("session_id", ""),
            "data": {
                "greeting_type": "personalized",
                "user_first_name": user_first_name,
                "detected_greeting": message_lower
            }
        }
    
    def _select_agent(self, message: str, context: Dict[str, Any]) -> Optional[Any]:
        """Select the most appropriate agent for the message"""
        message_lower = message.lower()
        print(f"🎯 AgentOrchestrator._select_agent: Message: {message_lower}")
        
        # Agent selection logic - ORDER MATTERS! Check more specific agents first
        employee_keywords = ["employee", "hr", "human resources", "staff", "personnel", "hire", "onboard employee", "employee record", "create employee", "add employee", "new employee", "software engineer", "department", "permanent", "full-time", "part-time", "employment type", "job title"]
        deliverable_keywords = ["deliverable", "project", "milestone", "task", "add deliverable", "create deliverable"]
        contract_keywords = ["client", "contract", "company", "agreement", "onboard"]
        time_keywords = ["timesheet", "log hours", "time entry", "productivity tracking", "work hours", "billable hours"]
        
        # Check employee agent FIRST (most specific)
        if any(keyword in message_lower for keyword in employee_keywords):
            print(f"🎯 AgentOrchestrator._select_agent: Selected employee agent")
            return self.agents["employee"]
        elif any(keyword in message_lower for keyword in deliverable_keywords):
            print(f"🎯 AgentOrchestrator._select_agent: Selected deliverable agent")
            return self.agents["deliverable"]
        elif any(keyword in message_lower for keyword in contract_keywords):
            print(f"🎯 AgentOrchestrator._select_agent: Selected contract agent")
            return self.agents["contract"]
        elif any(keyword in message_lower for keyword in time_keywords):
            print(f"🎯 AgentOrchestrator._select_agent: Selected time agent")
            return self.agents["time"]
        
        # Default to contract agent for general queries
        print(f"🎯 AgentOrchestrator._select_agent: Defaulting to contract agent")
        return self.agents["contract"]
    
    async def _check_workflow_intent(self, message: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if message should trigger a workflow - simplified to let agents handle most cases"""
        # For now, let individual agents handle client creation directly
        # Workflows can be added later for complex multi-step processes
        return None
    
    def _enhance_context_with_history(self, context: Dict[str, Any], current_message: str) -> Dict[str, Any]:
        """Enhance context with conversation history for better agent memory"""
        enhanced_context = context.copy()
        
        # Add conversation context markers
        enhanced_context["conversation_context"] = {
            "current_message": current_message,
            "message_type": "user_query",
            "requires_context": True,
            "timestamp": context.get("timestamp", ""),
            "session_id": context.get("session_id", "")
        }
        
        # Ensure conversation history is available
        if "conversation_history" in context:
            enhanced_context["recent_messages"] = context["conversation_history"][-5:]  # Last 5 messages
            enhanced_context["conversation_summary"] = {
                "total_messages": len(context["conversation_history"]),
                "user_messages": len([m for m in context["conversation_history"] if m.get("role") == "user"]),
                "agent_messages": len([m for m in context["conversation_history"] if m.get("role") == "assistant"])
            }
        
        # Add user context for personalization
        if "user_first_name" in context:
            enhanced_context["user_context"] = {
                "first_name": context["user_first_name"],
                "last_name": context.get("user_last_name", ""),
                "full_name": context.get("user_name", ""),
                "role": context.get("user_role", ""),
                "personalized": True
            }
        
        return enhanced_context
    
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of all agents"""
        capabilities = {}
        for name, agent in self.agents.items():
            capabilities[name] = agent.get_capabilities()
        
        return {
            "agents": capabilities,
            "workflows": list(self.workflows.keys()),
            "active_workflows": len(self.active_workflows)
        }
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow"""
        if workflow_id in self.active_workflows:
            state = self.active_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": state.status,
                "current_step": state.current_step,
                "completed_steps": state.completed_steps,
                "progress": len(state.completed_steps),
                "data": state.data
            }
        return None

from typing import Dict, Any, List, Optional
from backend.src.aiagents.contract_agent import ContractAgent
from backend.src.aiagents.time_agent import TimeTrackerAgent
from backend.src.aiagents.deliverable_agent import DeliverableAgent
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
            "deliverable": DeliverableAgent()
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
            result = await selected_agent.process_message(message, context)
            print(f"🎯 AgentOrchestrator: Agent result: {result}")
            return result
        
        # Fallback response
        fallback_result = {
            "agent": "System",
            "response": "I can help you with client management, time tracking, and project coordination. How can I assist you today?",
            "success": True
        }
        print(f"🎯 AgentOrchestrator: Returning fallback result: {fallback_result}")
        return fallback_result
    
    def _select_agent(self, message: str, context: Dict[str, Any]) -> Optional[Any]:
        """Select the most appropriate agent for the message"""
        message_lower = message.lower()
        print(f"🎯 AgentOrchestrator._select_agent: Message: {message_lower}")
        
        # Agent selection logic
        deliverable_keywords = ["deliverable", "project", "milestone", "task", "add deliverable", "create deliverable"]
        contract_keywords = ["client", "contract", "company", "agreement", "onboard"]
        time_keywords = ["time", "hours", "log", "timesheet", "productivity"]
        
        if any(keyword in message_lower for keyword in deliverable_keywords):
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

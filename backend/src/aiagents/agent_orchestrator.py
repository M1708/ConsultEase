from typing import Dict, Any, List, Optional
from backend.src.aiagents.contract_agent import ContractAgent
from backend.src.aiagents.time_agent import TimeTrackerAgent
from backend.src.aiagents.workflows.client_onboarding_workflow import ClientOnboardingWorkflow
from backend.src.aiagents.workflows.base_workflow import WorkflowState, WorkflowStatus
import uuid
from datetime import datetime

class MultiAgentOrchestrator:
    def __init__(self):
        # Initialize agents
        self.agents = {
            "contract": ContractAgent(),
            "time": TimeTrackerAgent()
        }
        
        # Initialize workflows
        self.workflows = {
            "client_onboarding": ClientOnboardingWorkflow()
        }
        
        # Active workflow tracking
        self.active_workflows: Dict[str, WorkflowState] = {}
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for processing user messages"""
        
        # Check if message is workflow-related
        workflow_result = await self._check_workflow_intent(message, context)
        if workflow_result:
            return workflow_result
        
        # Route to appropriate agent
        selected_agent = self._select_agent(message, context)
        
        if selected_agent:
            return await selected_agent.process_message(message, context)
        
        # Fallback response
        return {
            "agent": "System",
            "response": "I can help you with client management, time tracking, and project coordination. How can I assist you today?",
            "success": True
        }
    
    def _select_agent(self, message: str, context: Dict[str, Any]) -> Optional[Any]:
        """Select the most appropriate agent for the message"""
        message_lower = message.lower()
        
        # Agent selection logic
        contract_keywords = ["client", "contract", "company", "agreement", "onboard"]
        time_keywords = ["time", "hours", "log", "timesheet", "productivity"]
        
        if any(keyword in message_lower for keyword in contract_keywords):
            return self.agents["contract"]
        elif any(keyword in message_lower for keyword in time_keywords):
            return self.agents["time"]
        
        # Default to contract agent for general queries
        return self.agents["contract"]
    
    async def _check_workflow_intent(self, message: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if message should trigger a workflow"""
        message_lower = message.lower()
        
        # Client onboarding workflow triggers
        onboarding_triggers = ["onboard new client", "add new client company", "client setup"]
        
        if any(trigger in message_lower for trigger in onboarding_triggers):
            return await self._start_client_onboarding_workflow(message, context)
        
        return None
    
    async def _start_client_onboarding_workflow(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start client onboarding workflow"""
        try:
            # Create workflow state
            workflow_state = WorkflowState(
                workflow_id=str(uuid.uuid4()),
                user_id=context.get("user_id", "anonymous"),
                session_id=context.get("session_id", "default"),
                status=WorkflowStatus.IN_PROGRESS,
                current_step="validate_client_info",
                data={"client_info": self._extract_client_info_from_message(message)},
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            # Store workflow
            self.active_workflows[workflow_state.workflow_id] = workflow_state
            
            # Execute workflow
            workflow = self.workflows["client_onboarding"]
            final_state = await workflow.execute(workflow_state)
            
            # Update stored workflow
            self.active_workflows[workflow_state.workflow_id] = final_state
            
            if final_state.status == WorkflowStatus.COMPLETED:
                return {
                    "agent": "WorkflowManager",
                    "response": f"✅ Client onboarding completed successfully! Client ID: {final_state.data.get('client_id')}",
                    "success": True,
                    "workflow_id": final_state.workflow_id,
                    "data": final_state.data.get("onboarding_summary")
                }
            else:
                return {
                    "agent": "WorkflowManager",
                    "response": f"⚠️ Workflow failed: {final_state.error_message}",
                    "success": False,
                    "workflow_id": final_state.workflow_id
                }
                
        except Exception as e:
            return {
                "agent": "WorkflowManager",
                "response": f"❌ Failed to start onboarding workflow: {str(e)}",
                "success": False
            }
    
    def _extract_client_info_from_message(self, message: str) -> Dict[str, Any]:
        """Extract client information from user message"""
        # Simple extraction logic (can be enhanced with NLP)
        client_info = {}
        
        # Extract client name (look for patterns like "client called X" or "company named Y")
        import re
        name_patterns = [
            r'client (?:called|named) ([^,\s]+(?:\s+[^,\s]+)*)',
            r'company (?:called|named) ([^,\s]+(?:\s+[^,\s]+)*)',
            r'onboard ([^,\s]+(?:\s+[^,\s]+)*)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                client_info["client_name"] = match.group(1).strip()
                break
        
        # Extract industry (look for "in the X industry" patterns)
        industry_match = re.search(r'in the ([^,\s]+(?:\s+[^,\s]+)*) industry', message, re.IGNORECASE)
        if industry_match:
            client_info["industry"] = industry_match.group(1).strip()
        
        return client_info
    
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

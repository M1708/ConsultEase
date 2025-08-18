from backend.src.aiagents.workflows.base_workflow import BaseWorkflow, WorkflowState, WorkflowStatus
from backend.src.aiagents.contract_agent import ContractAgent
from langgraph.graph import END


class ClientOnboardingWorkflow(BaseWorkflow):
    def __init__(self):
        super().__init__("client_onboarding")
        self.contract_agent = ContractAgent()
    
    def setup_workflow(self):
        """Define client onboarding workflow steps"""
        
        # Add workflow nodes
        self.graph.add_node("validate_client_info", self.validate_client_info)
        self.graph.add_node("create_client_record", self.create_client_record)
        self.graph.add_node("setup_contacts", self.setup_contacts)
        self.graph.add_node("initialize_contracts", self.initialize_contracts)
        self.graph.add_node("complete_onboarding", self.complete_onboarding)
        
        # Define workflow edges
        self.graph.add_edge("validate_client_info", "create_client_record")
        self.graph.add_edge("create_client_record", "setup_contacts")
        self.graph.add_edge("setup_contacts", "initialize_contracts")
        self.graph.add_edge("initialize_contracts", "complete_onboarding")
        self.graph.add_edge("complete_onboarding", END)
        
        # Set entry point
        self.graph.set_entry_point("validate_client_info")
    
    async def validate_client_info(self, state: WorkflowState) -> WorkflowState:
        """Validate client information"""
        client_info = state.data.get("client_info", {})
        required_fields = ["client_name", "industry"]
        
        for field in required_fields:
            if field not in client_info:
                state.status = WorkflowStatus.FAILED
                state.error_message = f"Missing required field: {field}"
                return state
        
        state.current_step = "create_client_record"
        state.completed_steps.append("validate_client_info")
        return state
    
    async def create_client_record(self, state: WorkflowState) -> WorkflowState:
        """Create client record using ContractAgent"""
        try:
            client_info = state.data.get("client_info", {})
            
            # Get database session from the workflow context if available
            from backend.src.database.core.database import get_db
            db = next(get_db())
            
            result = await self.contract_agent.process_message(
                f"Create a client with name '{client_info.get('client_name')}' in the {client_info.get('industry')} industry",
                {
                    "user_id": state.user_id, 
                    "session_id": state.session_id,
                    "database": db
                }
            )
            
            if result["success"]:
                state.data["client_id"] = result.get("data", {}).get("client_id")
                state.current_step = "setup_contacts"
                state.completed_steps.append("create_client_record")
            else:
                state.status = WorkflowStatus.FAILED
                state.error_message = result["response"]
            
        except Exception as e:
            state.status = WorkflowStatus.FAILED
            state.error_message = str(e)
        
        return state
    
    async def setup_contacts(self, state: WorkflowState) -> WorkflowState:
        """Setup client contacts"""
        # Implementation for contact setup
        state.current_step = "initialize_contracts"
        state.completed_steps.append("setup_contacts")
        return state
    
    async def initialize_contracts(self, state: WorkflowState) -> WorkflowState:
        """Initialize contract templates"""
        # Implementation for contract initialization
        state.current_step = "complete_onboarding"
        state.completed_steps.append("initialize_contracts")
        return state
    
    async def complete_onboarding(self, state: WorkflowState) -> WorkflowState:
        """Complete the onboarding process"""
        state.status = WorkflowStatus.COMPLETED
        state.current_step = "completed"
        state.completed_steps.append("complete_onboarding")
        
        state.data["onboarding_summary"] = {
            "client_id": state.data.get("client_id"),
            "steps_completed": len(state.completed_steps),
            "completion_time": state.updated_at
        }
        
        return state

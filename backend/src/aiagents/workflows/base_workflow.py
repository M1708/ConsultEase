from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel
from langgraph.graph import StateGraph
from langgraph.graph import END
import uuid

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class WorkflowState(BaseModel):
    workflow_id: str
    user_id: str
    session_id: str
    status: WorkflowStatus
    current_step: str
    completed_steps: List[str] = []
    data: Dict[str, Any] = {}
    error_message: Optional[str] = None
    created_at: str
    updated_at: str

class BaseWorkflow:
    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.graph = StateGraph(WorkflowState)
        self.setup_workflow()
    
    def setup_workflow(self):
        """Override in subclasses to define workflow steps"""
        pass
    
    async def execute(self, initial_state: WorkflowState) -> WorkflowState:
        """Execute the workflow"""
        try:
            app = self.graph.compile()
            final_state_dict = await app.ainvoke(initial_state)
            
            # LangGraph returns a dictionary, convert back to WorkflowState
            if isinstance(final_state_dict, dict):
                return WorkflowState(**final_state_dict)
            else:
                return final_state_dict
                
        except Exception as e:
            initial_state.status = WorkflowStatus.FAILED
            initial_state.error_message = str(e)
            return initial_state

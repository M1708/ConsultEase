from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.src.database.core.database import get_db
from backend.src.aiagents.agent_orchestrator import MultiAgentOrchestrator
from datetime import datetime

router = APIRouter()

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    agent: str
    success: bool
    timestamp: str
    session_id: str
    workflow_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class WorkflowStatusRequest(BaseModel):
    workflow_id: str

# Initialize multi-agent orchestrator
orchestrator = MultiAgentOrchestrator()

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(chat: ChatMessage, db: Session = Depends(get_db)):
    """Send a message to the multi-agent system"""
    try:
        # Prepare context
        context = {
            "user_id": chat.user_id or "anonymous",
            "session_id": chat.session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "database": db,
            **(chat.context or {})
        }
        
        # Process through multi-agent orchestrator
        result = await orchestrator.process_message(chat.message, context)
        
        return ChatResponse(
            response=result["response"],
            agent=result["agent"],
            success=result["success"],
            timestamp=context["timestamp"],
            session_id=context["session_id"],
            workflow_id=result.get("workflow_id"),
            data=result.get("data")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@router.get("/agents")
async def list_available_agents():
    """List all available agents and their capabilities"""
    capabilities = orchestrator.get_agent_capabilities()
    return {
        "available_agents": capabilities["agents"],
        "available_workflows": capabilities["workflows"],
        "active_workflows": capabilities["active_workflows"]
    }

@router.post("/workflow/status")
async def get_workflow_status(request: WorkflowStatusRequest):
    """Get the status of a specific workflow"""
    status = await orchestrator.get_workflow_status(request.workflow_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return status

@router.get("/health")
async def agent_health_check():
    """Health check for the agent system"""
    try:
        capabilities = orchestrator.get_agent_capabilities()
        return {
            "status": "healthy",
            "agents_count": len(capabilities["agents"]),
            "workflows_available": len(capabilities["workflows"]),
            "active_workflows": capabilities["active_workflows"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent system unhealthy: {str(e)}")

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.src.database.core.database import get_db
from backend.src.aiagents.agent_orchestrator import MultiAgentOrchestrator
from datetime import datetime
from backend.src.auth.dependencies import get_current_user, AuthenticatedUser
from backend.src.auth.session_manager import SessionManager

router = APIRouter()
session_manager = SessionManager()

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatSessionStore(BaseModel): 
    session_id: str
    user_id: str
    chat_data: Dict[str, Any]


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
async def send_chat_message(
    chat: ChatMessage, 
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Send a message to the multi-agent system with authentication"""
    try:
        # Use authenticated user's information
        context = {
            "user_id": str(current_user.user_id),
            "session_id": current_user.session_id,
            "timestamp": datetime.now().isoformat(),
            "database": db,
            "user_role": current_user.role,
            "user_name": current_user.user.full_name or current_user.user.email,
            **(chat.context or {})
        }
        
        # Process through multi-agent orchestrator
        result = await orchestrator.process_message(chat.message, context)
        
        # Store chat interaction in Redis for session persistence
        chat_update = {
            "last_message": chat.message,
            "last_response": result["response"],
            "last_agent": result["agent"],
            "timestamp": context["timestamp"]
        }
        
        await session_manager.store_chat_session(
            current_user.session_id,
            str(current_user.user_id),
            chat_update
        )
        
        return ChatResponse(
            response=result["response"],
            agent=result["agent"],
            success=result["success"],
            timestamp=context["timestamp"],
            session_id=current_user.session_id,
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

@router.post("/session")
async def store_chat_session(
    request: ChatSessionStore,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Store chat session data in Redis"""
    # Verify user can only store their own session
    if request.user_id != str(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot store session for different user"
        )
    
    try:
        await session_manager.store_chat_session(
            request.session_id,
            request.user_id,
            request.chat_data
        )
        return {"message": "Chat session stored successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store chat session: {str(e)}"
        )

@router.get("/session/{session_id}")
async def get_chat_session(
    session_id: str,
    user_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get chat session data from Redis"""
    # Verify user can only access their own session
    if user_id != str(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access session for different user"
        )
    
    try:
        chat_data = await session_manager.get_chat_session(session_id, user_id)
        if not chat_data:
            return {"messages": []}  # Return empty if no session found
        
        return chat_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat session: {str(e)}"
        )

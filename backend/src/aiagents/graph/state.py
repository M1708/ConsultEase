from typing import List, TypedDict, Optional, Any, Dict
from datetime import datetime

class ConversationContext(TypedDict):
    """Context information for the current conversation"""
    user_id: str
    session_id: str
    user_name: str
    user_role: str
    conversation_start: str
    last_interaction: str
    interaction_count: int

class AgentMemory(TypedDict):
    """Memory information for agents"""
    conversation_history: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    context_summary: str
    previous_tasks: List[Dict[str, Any]]
    learned_patterns: Dict[str, Any]

class ErrorRecovery(TypedDict):
    """Error recovery and retry information"""
    error_count: int
    last_error: Optional[str]
    recovery_attempts: List[Dict[str, Any]]
    fallback_agent: Optional[str]

class AgentState(TypedDict):
    """Enhanced state for our agentic application with memory and context."""
    # Core message history
    messages: List[Any]
    
    # Current agent information
    current_agent: str
    previous_agent: Optional[str]
    agent_handoff_reason: Optional[str]
    
    # Data payload for workflows or tools
    data: Dict[str, Any]
    
    # Status tracking
    status: str  # e.g., "routing", "in_workflow", "failed", "complete", "agent_handoff"
    error_message: Optional[str]
    
    # Enhanced context and memory
    context: ConversationContext
    memory: AgentMemory
    error_recovery: ErrorRecovery
    
    # Agent coordination
    active_agents: List[str]  # Agents currently involved in the conversation
    pending_handoffs: List[Dict[str, Any]]  # Planned agent handoffs
    collaboration_mode: bool  # Whether multiple agents are collaborating
    
    # Performance tracking
    processing_start_time: Optional[str]
    agent_response_times: Dict[str, float]
    
    # Validation and quality
    input_validated: bool
    output_validated: bool
    quality_score: Optional[float]

def create_initial_state(
    user_id: str,
    session_id: str,
    user_name: str,
    user_role: str,
    initial_message: Any
) -> AgentState:
    """Create initial state for a new conversation"""
    current_time = datetime.now().isoformat()
    
    return AgentState(
        messages=[initial_message],
        current_agent="router",
        previous_agent=None,
        agent_handoff_reason=None,
        data={},
        status="routing",
        error_message=None,
        context=ConversationContext(
            user_id=user_id,
            session_id=session_id,
            user_name=user_name,
            user_role=user_role,
            conversation_start=current_time,
            last_interaction=current_time,
            interaction_count=1
        ),
        memory=AgentMemory(
            conversation_history=[],
            user_preferences={},
            context_summary="",
            previous_tasks=[],
            learned_patterns={}
        ),
        error_recovery=ErrorRecovery(
            error_count=0,
            last_error=None,
            recovery_attempts=[],
            fallback_agent=None
        ),
        active_agents=["router"],
        pending_handoffs=[],
        collaboration_mode=False,
        processing_start_time=current_time,
        agent_response_times={},
        input_validated=False,
        output_validated=False,
        quality_score=None
    )

def update_state_for_handoff(
    state: AgentState,
    new_agent: str,
    handoff_reason: str
) -> AgentState:
    """Update state when handing off to a new agent"""
    current_time = datetime.now().isoformat()
    
    # Update agent information
    state["previous_agent"] = state["current_agent"]
    state["current_agent"] = new_agent
    state["agent_handoff_reason"] = handoff_reason
    
    # Update active agents list
    if new_agent not in state["active_agents"]:
        state["active_agents"].append(new_agent)
    
    # Update context
    state["context"]["last_interaction"] = current_time
    state["context"]["interaction_count"] += 1
    
    # Update status
    state["status"] = "agent_handoff"
    
    return state

def update_memory(
    state: AgentState,
    new_context: str,
    user_preference: Optional[Dict[str, Any]] = None,
    task_completion: Optional[Dict[str, Any]] = None
) -> AgentState:
    """Update the memory component of the state"""
    # Update context summary
    if new_context:
        state["memory"]["context_summary"] = new_context
    
    # Update user preferences
    if user_preference:
        state["memory"]["user_preferences"].update(user_preference)
    
    # Add completed task
    if task_completion:
        state["memory"]["previous_tasks"].append(task_completion)
    
    return state

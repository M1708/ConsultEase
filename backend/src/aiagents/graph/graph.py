from langgraph.graph import StateGraph, END
from typing import Dict, Any

from .state import AgentState
from .router import router
from .nodes import contract_agent_node, employee_agent_node, client_agent_node, deliverable_agent_node, time_agent_node, user_agent_node # Import new node
from .tools import tool_executor_node

# Greeting node function
def greeting_node(state: AgentState) -> Dict:
    """Handle greeting messages with personalized responses"""
    try:
        # Get user name from context
        user_name = state.get('context', {}).get('user_name', '')
        
        # Extract first name if available
        first_name = user_name.split()[0] if user_name else ''
        
        # Create personalized greeting
        if first_name:
            greeting_response = f"Hello {first_name}! How can I help you today?"
        else:
            greeting_response = "Hello! How can I help you today?"
        
        # Create response message
        from langchain_core.messages import AIMessage
        response_message = AIMessage(content=greeting_response)
        
        return {"messages": [response_message]}
        
    except Exception as e:
        print(f"Error in greeting node: {e}")
        from langchain_core.messages import AIMessage
        response_message = AIMessage(content="Hello! How can I help you today?")
        return {"messages": [response_message]}

# This is the central definition of our agentic application graph.
workflow = StateGraph(AgentState)

# 1. Add the nodes to the graph
workflow.add_node("router", router)
workflow.add_node("greeting", greeting_node)
workflow.add_node("client_agent", client_agent_node) # Add new node
workflow.add_node("contract_agent", contract_agent_node)
workflow.add_node("employee_agent", employee_agent_node)
workflow.add_node("deliverable_agent", deliverable_agent_node)
workflow.add_node("time_agent", time_agent_node)
workflow.add_node("user_agent", user_agent_node)
workflow.add_node("tool_executor", tool_executor_node)

# 2. Set the entry point
workflow.set_entry_point("router")

# 3. Define the edges and conditional logic

# This conditional edge routes from the master router to the correct agent
workflow.add_conditional_edges(
    "router",
    lambda state: state["current_agent"],
    {
        "client_agent": "client_agent", # Add route to new agent
        "contract_agent": "contract_agent",
        "employee_agent": "employee_agent",
        "deliverable_agent": "deliverable_agent", # Add route to new agent
        "time_agent": "time_agent", # Add route to new agent
        "user_agent": "user_agent", # Add route to new agent
        "greeting": "greeting",
        "fallback": END,
    }
)

# Add edge from greeting node to END
workflow.add_edge("greeting", END)

# This function decides what to do after an agent has run
def after_agent_execution(state: AgentState) -> str:
    """Inspects the last message to see if it contains a tool call."""
    # 🚀 PHASE 2 OPTIMIZATION: Enhanced agent execution logic to prevent unnecessary iterations
    # TODO: If agents stop calling tools when needed, revert these optimizations
    
    last_message = state['messages'][-1]
    
    # 🚀 OPTIMIZATION: Check if this is a simple response that doesn't need tools
    if hasattr(last_message, 'content') and last_message.content:
        content = last_message.content.lower()
        # If the response is a simple acknowledgment or greeting, end immediately
        simple_responses = [
            "hello", "hi", "hey", "greetings", "thank you", "thanks", 
            "ok", "okay", "got it", "understood", "sure", "yes", "no"
        ]
        if any(response in content for response in simple_responses) and len(content) < 100:
            print(f"🛑 Early termination: Simple response detected, no tools needed")
            return END
    
    # 🚀 OPTIMIZATION: Check if we've already executed tools in this conversation
    if len(state['messages']) > 2:
        # Count tool calls in recent messages
        tool_call_count = 0
        for msg in state['messages'][-5:]:  # Check last 5 messages
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_call_count += len(msg.tool_calls)
        
        # If we've already made multiple tool calls, be more conservative
        if tool_call_count >= 2:
            print(f"🛑 Early termination: Multiple tool calls already executed ({tool_call_count})")
            return END
    
    # Original logic: check for tool calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool_executor"
    else:
        return END

# This function decides what to do after tool execution
def after_tool_execution(state: AgentState) -> str:
    """Decides whether to continue with the agent or end the conversation."""
    # 🚀 PERFORMANCE OPTIMIZATION: Track execution flow for contract search optimization
    # TODO: Remove debug statements once performance is optimized
    print(f"🔧 DEBUG: after_tool_execution called with {len(state['messages'])} messages")
    
    # 🚀 OPTIMIZATION: Early termination for successful tool results to prevent loops
    # TODO: If agents stop processing tool results properly, revert this optimization
    if len(state['messages']) > 0:
        last_message = state['messages'][-1]
        print(f"🔧 DEBUG: Last message type: {type(last_message)}")
        print(f"🔧 DEBUG: Last message role: {getattr(last_message, 'role', 'no role')}")
        
        # 🔧 FIX: Always let agent format tool results - remove early termination optimization
        # TODO: This ensures agent can format all tool results properly instead of returning raw JSON
        if isinstance(last_message, dict) and "content" in last_message:
            print(f"🔧 DEBUG: Last message is dict with content - letting agent format")
        elif hasattr(last_message, 'content') and last_message.content:
            print(f"🔧 DEBUG: Last message content preview: {str(last_message.content)[:200]}... - letting agent format")
        else:
            print(f"🔧 DEBUG: Last message has no content or content is empty")
    
    # CRITICAL FIX: After tool execution, always return to the current agent
    # so it can process and format the tool results
    print(f"🔧 DEBUG: Returning to agent: {state['current_agent']}")
    return state["current_agent"]

# After any agent runs, we check if we need to run tools
workflow.add_conditional_edges(
    "client_agent",
    after_agent_execution,
    {"tool_executor": "tool_executor", END: END}
)
workflow.add_conditional_edges(
    "contract_agent",
    after_agent_execution,
    {"tool_executor": "tool_executor", END: END}
)
workflow.add_conditional_edges(
    "employee_agent",
    after_agent_execution,
    {"tool_executor": "tool_executor", END: END}
)
workflow.add_conditional_edges(
    "deliverable_agent",
    after_agent_execution,
    {"tool_executor": "tool_executor", END: END}
)
workflow.add_conditional_edges(
    "time_agent",
    after_agent_execution,
    {"tool_executor": "tool_executor", END: END}
)
workflow.add_conditional_edges(
    "user_agent",
    after_agent_execution,
    {"tool_executor": "tool_executor", END: END}
)

# After the tool executor runs, decide whether to continue or end
workflow.add_conditional_edges(
    "tool_executor",
    after_tool_execution,
    {
        "client_agent": "client_agent",
        "contract_agent": "contract_agent",
        "employee_agent": "employee_agent",
        "deliverable_agent": "deliverable_agent",
        "time_agent": "time_agent",
        "user_agent": "user_agent",
        END: END
    }
)

# 4. Compile the graph into a runnable application
app = workflow.compile()

print("✅ Agentic graph compiled successfully with all agents!")

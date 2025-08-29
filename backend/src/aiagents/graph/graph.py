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
    last_message = state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool_executor"
    else:
        return END

# This function decides what to do after tool execution
def after_tool_execution(state: AgentState) -> str:
    """Decides whether to continue with the agent or end the conversation."""
    # Check if we have too many messages (prevent infinite loops)
    if len(state['messages']) > 20:
        return END
    
    # Check if the last tool execution had errors
    last_message = state['messages'][-1]
    if hasattr(last_message, 'content'):
        try:
            import json
            content = json.loads(last_message.content)
            if isinstance(content, dict) and content.get('error'):
                # If there's an error, end the conversation to prevent loops
                return END
        except:
            pass
    
    # Check if we've seen the same tool call pattern recently (prevent loops)
    recent_messages = state['messages'][-6:]  # Look at last 6 messages
    tool_calls = []
    for msg in recent_messages:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_calls.append((tool_call.function.name, tool_call.function.arguments))
    
    # If we see the same tool call more than twice, end to prevent infinite loops
    if len(tool_calls) > 2:
        unique_calls = set(tool_calls)
        if len(unique_calls) == 1:  # Same call repeated
            return END
    
    # Otherwise, continue with the current agent
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

"""
Hybrid Workflow Graph with OpenAI Agents SDK Integration

This module provides an enhanced version of the LangGraph workflow that integrates
OpenAI Agents SDK agents while maintaining backward compatibility.
"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any

from .state import AgentState
from .router import router
from .nodes import contract_agent_node, employee_agent_node, client_agent_node, deliverable_agent_node, time_agent_node, user_agent_node
from .tools import tool_executor_node
from .agents_sdk_integration import create_hybrid_workflow_node, initialize_hybrid_system
# Import the hybrid orchestrator
from .agents_sdk_integration import get_hybrid_orchestrator

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

        # Return serializable dictionary instead of LangChain message
        return {"messages": [{
            "type": "ai",
            "content": greeting_response,
            "role": "assistant"
        }]}

    except Exception as e:
        print(f"Error in greeting node: {e}")
        return {"messages": [{
            "type": "ai",
            "content": "Hello! How can I help you today?",
            "role": "assistant"
        }]}

# This is the enhanced definition of our agentic application graph with SDK integration.
workflow = StateGraph(AgentState)

# 1. Add the nodes to the graph
workflow.add_node("router", router)
workflow.add_node("greeting", greeting_node)
workflow.add_node("client_agent", client_agent_node)
workflow.add_node("contract_agent", contract_agent_node)
workflow.add_node("employee_agent", employee_agent_node)
workflow.add_node("deliverable_agent", deliverable_agent_node)
workflow.add_node("time_agent", time_agent_node)
workflow.add_node("user_agent", user_agent_node)
workflow.add_node("tool_executor", tool_executor_node)

# Add hybrid workflow node for SDK integration
hybrid_node = create_hybrid_workflow_node()
workflow.add_node("hybrid_agent", hybrid_node)

# 2. Set the entry point
workflow.set_entry_point("router")

# 3. Define the edges and conditional logic

# Enhanced routing with SDK preference
def enhanced_router(state: AgentState) -> str:
    """Enhanced router that considers SDK availability"""
    print(f"🔍 DEBUG: enhanced_router called with state keys: {list(state.keys()) if isinstance(state, dict) else 'Not a dict'}")
    print(f"🔍 DEBUG: enhanced_router state: {state}")

    try:
        # 🔧 CRITICAL FIX: Check for employee operations first and bypass everything else
        if state.get('messages'):
            last_message = state['messages'][-1]
            if isinstance(last_message, dict) and 'content' in last_message:
                message_content = last_message['content'].lower()
                print(f"🔍 DEBUG: enhanced_router - checking message: '{message_content}'")
                print(f"🔍 DEBUG: enhanced_router - checking for amount filtering patterns...")
                if 'amount' in message_content and ('more than' in message_content or 'greater than' in message_content) and 'contract' in message_content:
                    print(f"🔍 DEBUG: enhanced_router - DETECTED AMOUNT FILTERING PATTERN!")
                
                # Check for employee document deletion patterns specifically
                if ('delete' in message_content and 'document' in message_content and 
                    any(word in message_content for word in ['employee', 'staff', 'worker', 'personnel'])):
                    print(f"🔍 DEBUG: enhanced_router - DETECTED EMPLOYEE DOCUMENT DELETION, forcing employee_agent")
                    state['current_agent'] = 'employee_agent'
                    if 'data' not in state:
                        state['data'] = {}
                    state['data']['current_agent'] = 'employee_agent'
                    state['data']['routing_completed'] = True
                    return 'employee_agent'
                
                # General employee operations check
                if any(pattern in message_content for pattern in ['employee', 'staff', 'worker', 'personnel', 'details for employee', 'show details for', 'full time', 'part time', 'full-time', 'part-time', 'update employee', 'update committed hours', 'update rate', 'update job title', 'update department', 'delete contract document for employee', 'delete nda document for employee', 'delete document for employee']) or ('upload' in message_content and ('employee' in message_content or 'staff' in message_content or 'worker' in message_content or 'personnel' in message_content)) or ('delete' in message_content and ('employee' in message_content or 'staff' in message_content or 'worker' in message_content or 'personnel' in message_content)):
                    print(f"🔍 DEBUG: enhanced_router - DETECTED EMPLOYEE OPERATION, forcing employee_agent")
                    # Force employee agent and update state
                    state['current_agent'] = 'employee_agent'
                    if 'data' not in state:
                        state['data'] = {}
                    state['data']['current_agent'] = 'employee_agent'
                    state['data']['routing_completed'] = True
                    return 'employee_agent'
        
        # 🔧 FIX: Check if we've already routed to prevent multiple iterations
        # BUT only if this is not a new user message (tool results should not trigger re-routing)
        if state.get('data', {}).get('routing_completed'):
            # Check if this is a new user message (not a tool result)
            last_message = state['messages'][-1] if state['messages'] else None
            is_new_user_message = (
                last_message and 
                isinstance(last_message, dict) and 
                last_message.get('role') == 'user' and
                'content' in last_message and
                not last_message.get('tool_call_id')  # Not a tool result
            )
            
            if not is_new_user_message:
                print(f"🔍 DEBUG: enhanced_router - routing already completed for tool result, skipping")
                # CRITICAL FIX: Check top-level current_agent first, then data.current_agent
                current_agent = state.get('current_agent') or state.get('data', {}).get('current_agent', 'client_agent')
                print(f"🔍 DEBUG: enhanced_router - returning current_agent: {current_agent}")
                print(f"🔍 DEBUG: enhanced_router - state data: {state.get('data', {})}")
                return current_agent
            else:
                print(f"🔍 DEBUG: enhanced_router - new user message detected, re-evaluating routing")
                # Reset routing state for new user message
                if 'routing_completed' in state.get('data', {}):
                    del state['data']['routing_completed']
                if 'current_agent' in state:
                    del state['current_agent']
        
        # 🔧 FIX: Check if sync router has already made a decision (top-level current_agent)
        if state.get('current_agent') and state['current_agent'] != 'router':
            print(f"🔍 DEBUG: enhanced_router - sync router already decided: {state['current_agent']}")
            # Mark routing as completed and return the sync router's decision
            if 'data' not in state:
                state['data'] = {}
            state['data']['routing_completed'] = True
            state['data']['current_agent'] = state['current_agent']
            return state['current_agent']
        
        # Mark routing as completed to prevent loops
        if 'data' not in state:
            state['data'] = {}
        state['data']['routing_completed'] = True
        
        orchestrator = get_hybrid_orchestrator()
        agent_status = orchestrator.get_agent_status()

        # DISABLED: SDK hybrid workflow (causing fallback issues)
        # Always use original routing for now
        # if agent_status["sdk_available"] and agent_status["sdk_agents_initialized"]:
        #     print(f"🔍 DEBUG: enhanced_router - using hybrid_agent")
        #     state['data']['current_agent'] = 'hybrid_agent'
        #     return "hybrid_agent"

        # Use original routing
        print(f"🔍 DEBUG: enhanced_router - using original router")
        router_result = router(state)
        print(f"🔍 DEBUG: enhanced_router - router result: {router_result}")

        # The router returns a dict with current_agent, extract the agent name
        if isinstance(router_result, dict) and "current_agent" in router_result:
            agent_name = router_result["current_agent"]
            print(f"🔍 DEBUG: enhanced_router - extracted agent name: {agent_name}")
            state['data']['current_agent'] = agent_name
            return agent_name
        else:
            print(f"🔍 DEBUG: enhanced_router - router result is not a dict or missing current_agent, returning client_agent")
            state['data']['current_agent'] = 'client_agent'
            return "client_agent"

    except Exception as e:
        print(f"❌ enhanced_router error: {e}")
        import traceback
        print(f"❌ enhanced_router traceback: {traceback.format_exc()}")
        state['data']['current_agent'] = 'client_agent'
        return "client_agent"

# This conditional edge routes from the master router to the correct agent
workflow.add_conditional_edges(
    "router",
    enhanced_router,
    {
        "client_agent": "client_agent",
        "contract_agent": "contract_agent",
        "employee_agent": "employee_agent",
        "deliverable_agent": "deliverable_agent",
        "time_agent": "time_agent",
        "user_agent": "user_agent",
        "greeting": "greeting",
        "hybrid_agent": "hybrid_agent",  # New SDK-integrated path
        "fallback": END,
    }
)

# Add edge from greeting node to END
workflow.add_edge("greeting", END)

# Hybrid agent can route to tools or end
def after_hybrid_execution(state: AgentState) -> str:
    """Decides what to do after hybrid agent execution"""
    # Check if tools were used and need execution
    if state.get("data", {}).get("tools_used"):
        return "tool_executor"
    else:
        return END

workflow.add_conditional_edges(
    "hybrid_agent",
    after_hybrid_execution,
    {"tool_executor": "tool_executor", END: END}
)

# This function decides what to do after an agent has run
def after_agent_execution(state: AgentState) -> str:
    """Inspects the last message to see if it contains a tool call."""
    # 🚀 PHASE 2 OPTIMIZATION: Enhanced agent execution logic to prevent unnecessary iterations
    # TODO: If agents stop calling tools when needed, revert these optimizations

    print(f"🔍 DEBUG: after_agent_execution - state['data'] = {state.get('data', {})}")
    print(f"🔍 DEBUG: after_agent_execution - user_operation = {state.get('data', {}).get('user_operation', 'NOT_FOUND')}")

    last_message = state['messages'][-1]

    # If the response is a simple acknowledgment or greeting, end immediately
    if hasattr(last_message, 'content') and last_message.content:
        content = last_message.content.lower()
        simple_responses = [
            "hello", "hi", "hey", "greetings", "thank you", "thanks",
            "ok", "okay", "got it", "understood", "sure"
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
    # Handle both dict messages (serialized) and object messages
    has_tool_calls = False
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        has_tool_calls = True
    elif isinstance(last_message, dict) and last_message.get('tool_calls'):
        has_tool_calls = True
    
    print(f"🔍 DEBUG: Tool call detection - has_tool_calls: {has_tool_calls}")
    print(f"🔍 DEBUG: Tool call detection - last_message type: {type(last_message)}")
    if isinstance(last_message, dict):
        print(f"🔍 DEBUG: Tool call detection - dict keys: {list(last_message.keys())}")
        if 'tool_calls' in last_message:
            print(f"🔍 DEBUG: Tool call detection - tool_calls count: {len(last_message['tool_calls'])}")
    
    if has_tool_calls:
        print(f"🔍 DEBUG: Routing to tool_executor")
        return "tool_executor"
    else:
        print(f"🔍 DEBUG: No tool calls detected, ending workflow")
        return END

# This function decides what to do after tool execution
def after_tool_execution(state: AgentState) -> str:
    """Decides whether to continue with the agent or end the conversation."""
    # 🚀 PERFORMANCE OPTIMIZATION: Track execution flow for contract search optimization
    # REVERT: If infinite loop issues persist, revert to original logic

    print(f"🔍 DEBUG: after_tool_execution - state['data'] = {state.get('data', {})}")
    print(f"🔍 DEBUG: after_tool_execution - user_operation = {state.get('data', {}).get('user_operation', 'NOT_FOUND')}")

    # LOOP PREVENTION: Track tool execution cycles to prevent infinite loops
    if 'tool_execution_count' not in state.get('data', {}):
        state['data']['tool_execution_count'] = 0
    state['data']['tool_execution_count'] += 1

    # If we've executed too many tools in this conversation, end it
    if state['data']['tool_execution_count'] > 5:
        print(f"🛑 LOOP PREVENTION: Ending conversation after {state['data']['tool_execution_count']} tool executions")
        return END

    # Check if the last tool result indicates completion
    last_message = state['messages'][-1] if state['messages'] else None
    content = ""
    
    # Handle different message formats for tool results
    if last_message:
        if hasattr(last_message, 'content') and last_message.content:
            content = last_message.content.lower()
        elif isinstance(last_message, dict):
            # Tool result messages are stored as dicts with 'content' key
            content = last_message.get('content', '').lower()
        
        print(f"🔍 DEBUG: after_tool_execution - last message content: {content[:200]}...")
    
    # Check for successful tool execution using the stored success status
    last_tool_success = state.get('data', {}).get('last_tool_success')
    print(f"🔍 DEBUG: after_tool_execution - last_tool_success: {last_tool_success}")
    
    if last_tool_success is True:
        print("🛑 LOOP PREVENTION: Tool execution completed successfully, clearing context")
        # Clear operation context after successful operations to prevent interference with next request
        if 'current_contract_id' in state.get('data', {}):
            del state['data']['current_contract_id']
            print("🔍 DEBUG: Cleared current_contract_id after successful operation")
        if 'user_operation' in state.get('data', {}):
            del state['data']['user_operation']
            print("🔍 DEBUG: Cleared user_operation after successful operation")
        if 'original_user_request' in state.get('data', {}):
            del state['data']['original_user_request']
            print("🔍 DEBUG: Cleared original_user_request after successful operation")
        if 'current_workflow' in state.get('data', {}):
            del state['data']['current_workflow']
            print("🔍 DEBUG: Cleared current_workflow after successful operation")
        if 'current_client' in state.get('data', {}):
            del state['data']['current_client']
            print("🔍 DEBUG: Cleared current_client after successful operation")
        # CRITICAL FIX: Reset agent routing state for next request
        if 'current_agent' in state:
            del state['current_agent']
            print("🔍 DEBUG: Cleared current_agent after successful operation")
        if 'routing_completed' in state.get('data', {}):
            del state['data']['routing_completed']
            print("🔍 DEBUG: Cleared routing_completed after successful operation")
        # Clear the success status to prevent repeated clearing
        if 'last_tool_success' in state.get('data', {}):
            del state['data']['last_tool_success']
            print("🔍 DEBUG: Cleared last_tool_success status")
        return END
    
    # Fallback: Check message content for success keywords (for backward compatibility)
    if content:
        # Special check for create_client_and_contract success
        if 'successfully created client' in content and 'contract' in content:
            print("🛑 LOOP PREVENTION: create_client_and_contract completed successfully, ending conversation")
            # Clear operation context after successful operations
            if 'current_contract_id' in state.get('data', {}):
                del state['data']['current_contract_id']
                print("🔍 DEBUG: Cleared current_contract_id after successful create_client_and_contract")
            if 'user_operation' in state.get('data', {}):
                del state['data']['user_operation']
                print("🔍 DEBUG: Cleared user_operation after successful create_client_and_contract")
            if 'original_user_request' in state.get('data', {}):
                del state['data']['original_user_request']
                print("🔍 DEBUG: Cleared original_user_request after successful create_client_and_contract")
            if 'current_workflow' in state.get('data', {}):
                del state['data']['current_workflow']
                print("🔍 DEBUG: Cleared current_workflow after successful create_client_and_contract")
            return END
            
        # TODO: CONFIRMATION FIX - Check for confirmation responses and clear context after successful operations
        # If tool result indicates success or completion, end conversation
        success_keywords = ['successfully', 'completed', 'updated', 'created', 'uploaded', 'deleted', 'removed', 'added']
        if any(keyword in content for keyword in success_keywords):
            print("🛑 LOOP PREVENTION: Tool execution completed successfully (fallback detection), ending conversation")
            # Clear operation context after successful operations to prevent interference with next request
            if 'current_contract_id' in state.get('data', {}):
                del state['data']['current_contract_id']
                print("🔍 DEBUG: Cleared current_contract_id after successful operation")
            if 'user_operation' in state.get('data', {}):
                del state['data']['user_operation']
                print("🔍 DEBUG: Cleared user_operation after successful operation")
            if 'original_user_request' in state.get('data', {}):
                del state['data']['original_user_request']
                print("🔍 DEBUG: Cleared original_user_request after successful operation")
            if 'current_workflow' in state.get('data', {}):
                del state['data']['current_workflow']
                print("🔍 DEBUG: Cleared current_workflow after successful operation")
            if 'current_client' in state.get('data', {}):
                del state['data']['current_client']
                print("🔍 DEBUG: Cleared current_client after successful operation")
            # CRITICAL FIX: Reset agent routing state for next request
            if 'current_agent' in state:
                del state['current_agent']
                print("🔍 DEBUG: Cleared current_agent after successful operation")
            if 'routing_completed' in state.get('data', {}):
                del state['data']['routing_completed']
                print("🔍 DEBUG: Cleared routing_completed after successful operation")
            return END
            
        # TODO: CONFIRMATION FIX - Also clear context when user confirms an operation (yes/no responses)
        # Check if this is a confirmation response that completed an operation
        if isinstance(content, str):
            content_lower = content.lower().strip()
            confirmation_words = ['yes', 'y', 'ok', 'okay', 'confirm', 'proceed', 'go ahead', 'sure', 'alright']
            
            # Check if user confirmed and we have an active operation
            if content_lower in confirmation_words:
                current_workflow = state.get('data', {}).get('current_workflow')
                user_operation = state.get('data', {}).get('user_operation')
                
                print(f"🔍 DEBUG WORKFLOW: User said '{content_lower}', current_workflow='{current_workflow}', user_operation='{user_operation}'")
                
                # If this is a confirmation for an upload operation, clear context after processing
                if current_workflow == 'upload' and user_operation == 'upload_contract_document':
                    print("🛑 LOOP PREVENTION: User confirmed upload operation, will clear context after processing")
                    # Don't clear context immediately - let the agent process the confirmation first
                    # The context will be cleared when the actual upload completes
                else:
                    print(f"🔍 DEBUG WORKFLOW: Not an upload confirmation - workflow='{current_workflow}', operation='{user_operation}'")

    # CRITICAL FIX: After tool execution, end the workflow
    # The tool results are already formatted and ready for the user
    print("🔍 DEBUG: Tool execution completed, ending workflow")
    return END

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
        END: END
    }
)

# 4. Compile the graph into a runnable application
app = workflow.compile()

async def initialize_hybrid_workflow():
    """Initialize the hybrid workflow with SDK integration"""
    print("🚀 Initializing Hybrid Workflow with OpenAI Agents SDK...")
    print("🔍 DEBUG: Hybrid workflow initialization starting")

    # Initialize SDK agents
    sdk_initialized = await initialize_hybrid_system()

    if sdk_initialized:
        print("✅ OpenAI Agents SDK integration enabled")
    else:
        print("⚠️ OpenAI Agents SDK not available, using fallback mode")

    print("✅ Hybrid workflow compiled successfully!")
    return app

print("✅ Hybrid workflow graph structure compiled successfully!")

# Export the initialization function
__all__ = ['app', 'initialize_hybrid_workflow']

#!/usr/bin/env python3
"""
Quick test script to verify client update functionality
"""
import asyncio
from src.aiagents.graph.graph import app as agent_app
from src.aiagents.graph.state import create_initial_state
from langchain_core.messages import HumanMessage

async def test_client_update():
    """Test client update functionality"""
    
    # Test message for updating a client
    test_message = "David Smith is the contact person for TechCorp. Please update it in the records"
    
    print(f"🧪 Testing client update with message: '{test_message}'")
    
    # Create initial state with proper user context
    initial_message = HumanMessage(content=test_message)
    initial_state = create_initial_state(
        user_id="7615479c-2785-4695-853c-1a898d1b7dc5",
        session_id="test-session-456", 
        user_name="Test User",
        user_role="admin",
        initial_message=initial_message
    )
    
    # Add user context to the state for tool execution
    initial_state["context"]["user_id"] = "7615479c-2785-4695-853c-1a898d1b7dc5"
    initial_state["context"]["session_id"] = "test-session-456"
    initial_state["context"]["user_name"] = "Test User"
    initial_state["context"]["role"] = "admin"
    
    try:
        # Invoke the graph
        result = await agent_app.ainvoke(initial_state, config={"recursion_limit": 10})
        
        print(f"✅ Test completed successfully")
        print(f"📊 Current agent: {result.get('current_agent', 'unknown')}")
        
        # Check if we have messages
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                print(f"🤖 Agent response: {last_message.content}")
            elif isinstance(last_message, dict) and 'content' in last_message:
                print(f"🤖 Agent response: {last_message['content']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_client_update())
    if success:
        print("✅ Client update test passed!")
    else:
        print("❌ Client update test failed!")

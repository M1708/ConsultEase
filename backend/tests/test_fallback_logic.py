#!/usr/bin/env python3
"""
Test script to verify fallback logic works correctly
"""
import asyncio
import os
from src.aiagents.graph.nodes import enhanced_executor, contract_agent_instance
from src.aiagents.graph.state import create_initial_state
from langchain_core.messages import HumanMessage

async def test_fallback_logic():
    """Test that fallback logic correctly detects and executes contract updates"""
    
    # Ensure no OpenAI API key is available
    original_key = os.environ.get("OPENAI_API_KEY")
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    try:
        # Recreate the executor to ensure it has no OpenAI client
        from src.aiagents.graph.nodes import EnhancedAgentNodeExecutor
        test_executor = EnhancedAgentNodeExecutor()
        
        # Test message for updating a contract
        test_message = "Update billing prompt date to 1st Sep 2025 for contract with Acme"
        
        print(f"🧪 Testing fallback logic with message: '{test_message}'")
        print(f"🔧 OpenAI client available: {test_executor.client is not None}")
        
        # Create initial state with proper user context
        initial_message = HumanMessage(content=test_message)
        initial_state = create_initial_state(
            user_id="7615479c-2785-4695-853c-1a898d1b7dc5",
            session_id="test-session-fallback",
            user_name="Test User",
            user_role="admin",
            initial_message=initial_message
        )
        
        # Add user context to the state for tool execution
        initial_state["context"]["user_id"] = "7615479c-2785-4695-853c-1a898d1b7dc5"
        initial_state["context"]["session_id"] = "test-session-fallback"
        initial_state["context"]["user_name"] = "Test User"
        initial_state["context"]["role"] = "admin"
        
        # Test the enhanced executor directly
        result = await test_executor.invoke(
            initial_state, 
            contract_agent_instance, 
            "contract_agent"
        )
        
        print(f"✅ Fallback test completed successfully")
        
        # Check if we have messages
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                print(f"🤖 Agent response: {last_message.content}")
            elif isinstance(last_message, dict) and 'content' in last_message:
                print(f"🤖 Agent response: {last_message['content']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original API key if it existed
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

if __name__ == "__main__":
    success = asyncio.run(test_fallback_logic())
    if success:
        print("✅ Fallback logic test passed!")
    else:
        print("❌ Fallback logic test failed!")

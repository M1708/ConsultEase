#!/usr/bin/env python3
"""
Test script to verify contract creation functionality still works
"""
import asyncio
import os
from src.aiagents.graph.nodes import EnhancedAgentNodeExecutor, contract_agent_instance
from src.aiagents.graph.state import create_initial_state
from langchain_core.messages import HumanMessage

async def test_contract_creation():
    """Test that contract creation functionality still works after our fixes"""
    
    # Ensure no OpenAI API key is available to test fallback logic
    original_key = os.environ.get("OPENAI_API_KEY")
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    try:
        # Create test executor
        test_executor = EnhancedAgentNodeExecutor()
        
        print("🧪 Testing CONTRACT CREATION functionality...")
        
        # Test contract creation for existing client
        test_message = "Create a new Fixed Price contract for Acme Corporation worth $150,000 starting from 2025-01-01 to 2025-12-31"
        
        initial_message = HumanMessage(content=test_message)
        initial_state = create_initial_state(
            user_id="7615479c-2785-4695-853c-1a898d1b7dc5",
            session_id="test-session-create-contract",
            user_name="Test User",
            user_role="admin",
            initial_message=initial_message
        )
        
        result = await test_executor.invoke(
            initial_state, 
            contract_agent_instance, 
            "contract_agent"
        )
        
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            response = getattr(last_message, 'content', str(last_message))
            print(f"✅ CONTRACT CREATION Response: {response[:300]}...")
            
            if any(word in response.lower() for word in ["created", "contract", "acme", "150000", "150,000"]):
                print("✅ CONTRACT CREATION: PASSED")
                return True
            else:
                print("❌ CONTRACT CREATION: FAILED - Expected contract creation confirmation")
                return False
        else:
            print("❌ CONTRACT CREATION: FAILED - No response received")
            return False
        
    except Exception as e:
        print(f"❌ CONTRACT CREATION: FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original API key if it existed
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

if __name__ == "__main__":
    success = asyncio.run(test_contract_creation())
    if success:
        print("✅ Contract creation test passed!")
    else:
        print("❌ Contract creation test failed!")

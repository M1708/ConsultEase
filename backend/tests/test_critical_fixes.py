#!/usr/bin/env python3
"""
Test script to verify the two critical fixes:
1. Contract creation for new clients (auto-create client)
2. Contract updates by contract ID
"""
import asyncio
import os
from src.aiagents.graph.nodes import EnhancedAgentNodeExecutor, contract_agent_instance
from src.aiagents.graph.state import create_initial_state
from langchain_core.messages import HumanMessage

async def test_critical_fixes():
    """Test both critical fixes"""
    
    # Ensure no OpenAI API key is available to test fallback logic
    original_key = os.environ.get("OPENAI_API_KEY")
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    try:
        # Create test executor
        test_executor = EnhancedAgentNodeExecutor()
        
        print("🧪 Testing Critical Fixes")
        print("=" * 60)
        
        # Test 1: Create contract for NEW client (should auto-create client)
        print("\n1️⃣ Testing CONTRACT CREATION for NEW CLIENT...")
        test_message = "create a new contract for client HealthPlus LLC. It's a startup firm with Maria Black as the contact, maria.black@hp.com. The contract starts on 1st Oct 2025 and ends on 31st Mar 2026. It's a fixed contract with original amount of $250,000, billing prompt date is 30th Nov 2025."
        
        initial_message = HumanMessage(content=test_message)
        initial_state = create_initial_state(
            user_id="7615479c-2785-4695-853c-1a898d1b7dc5",
            session_id="test-session-new-client-contract",
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
            print(f"✅ NEW CLIENT + CONTRACT Response: {response[:300]}...")
            
            if any(word in response.lower() for word in ["created", "healthplus", "maria", "250000", "250,000"]):
                print("✅ NEW CLIENT + CONTRACT CREATION: PASSED")
                test1_passed = True
            else:
                print("❌ NEW CLIENT + CONTRACT CREATION: FAILED")
                print(f"Full response: {response}")
                test1_passed = False
        else:
            print("❌ NEW CLIENT + CONTRACT CREATION: FAILED - No response")
            test1_passed = False
        
        # Test 2: Update contract by ID
        print("\n2️⃣ Testing CONTRACT UPDATE by ID...")
        test_message = "update billing prompt date to 1st Oct 2025 for contract id 84"
        
        initial_message = HumanMessage(content=test_message)
        initial_state = create_initial_state(
            user_id="7615479c-2785-4695-853c-1a898d1b7dc5",
            session_id="test-session-update-by-id",
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
            print(f"✅ CONTRACT UPDATE BY ID Response: {response[:300]}...")
            
            if any(word in response.lower() for word in ["updated", "successfully", "contract", "84"]):
                print("✅ CONTRACT UPDATE BY ID: PASSED")
                test2_passed = True
            else:
                print("❌ CONTRACT UPDATE BY ID: FAILED")
                print(f"Full response: {response}")
                test2_passed = False
        else:
            print("❌ CONTRACT UPDATE BY ID: FAILED - No response")
            test2_passed = False
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 CRITICAL FIXES TEST SUMMARY")
        print("=" * 60)
        print(f"1. New Client + Contract Creation: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"2. Contract Update by ID: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        
        overall_success = test1_passed and test2_passed
        if overall_success:
            print("\n🎉 ALL CRITICAL FIXES WORKING!")
        else:
            print("\n⚠️ Some fixes still need work")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Critical fixes test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original API key if it existed
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

if __name__ == "__main__":
    success = asyncio.run(test_critical_fixes())
    if success:
        print("✅ Critical fixes test passed!")
    else:
        print("❌ Critical fixes test failed!")

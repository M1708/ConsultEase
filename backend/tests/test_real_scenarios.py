#!/usr/bin/env python3
"""
Test the two critical scenarios with the actual application flow
(using OpenAI function calling, not fallback mode)
"""
import asyncio
import os
from src.aiagents.graph.nodes import EnhancedAgentNodeExecutor, contract_agent_instance
from src.aiagents.graph.state import create_initial_state
from langchain_core.messages import HumanMessage

async def test_real_scenarios():
    """Test the two critical scenarios with OpenAI function calling"""
    
    # Set a dummy OpenAI API key to test the actual flow (not fallback)
    original_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "test-key-for-function-calling"
    
    try:
        # Create test executor
        test_executor = EnhancedAgentNodeExecutor()
        
        print("🧪 TESTING REAL SCENARIOS (with OpenAI function calling)")
        print("=" * 80)
        
        # Test 1: Create contract for NEW client
        print("\n1️⃣ Testing CONTRACT CREATION for NEW CLIENT...")
        print("User message: create a new contract for client HealthPlus LLC. It's a startup firm with Maria Black as the contact, maria.black@hp.com. The contract starts on 1st Oct 2025 and ends on 31st Mar 2026. It's a fixed contract with original amount of $250,000, billing prompt date is 30th Nov 2025.")
        
        test_message = "create a new contract for client HealthPlus LLC. It's a startup firm with Maria Black as the contact, maria.black@hp.com. The contract starts on 1st Oct 2025 and ends on 31st Mar 2026. It's a fixed contract with original amount of $250,000, billing prompt date is 30th Nov 2025."
        
        initial_message = HumanMessage(content=test_message)
        initial_state = create_initial_state(
            user_id="7615479c-2785-4695-853c-1a898d1b7dc5",
            session_id="test-session-real-new-client",
            user_name="Test User",
            user_role="admin",
            initial_message=initial_message
        )
        
        try:
            result = await test_executor.invoke(
                initial_state, 
                contract_agent_instance, 
                "contract_agent"
            )
            
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                response = getattr(last_message, 'content', str(last_message))
                print(f"✅ Agent Response: {response}")
                
                # Check if the agent is trying to use the right tool
                if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                    tool_calls = last_message.tool_calls
                    print(f"🔧 Tool calls made: {[tc.function.name for tc in tool_calls]}")
                    
                    # Check if create_client_and_contract is being called
                    if any(tc.function.name == "create_client_and_contract" for tc in tool_calls):
                        print("✅ SUCCESS: Agent correctly identified this as a new client + contract scenario")
                        print("✅ Agent is calling 'create_client_and_contract' tool")
                    else:
                        print("❌ ISSUE: Agent should call 'create_client_and_contract' but called:", [tc.function.name for tc in tool_calls])
                else:
                    print("❌ ISSUE: Agent didn't make any tool calls")
            else:
                print("❌ ISSUE: No response from agent")
                
        except Exception as e:
            print(f"❌ Error in test 1: {e}")
        
        print("\n" + "-" * 80)
        
        # Test 2: Update contract by ID
        print("\n2️⃣ Testing CONTRACT UPDATE by ID...")
        print("User message: update billing prompt date to 1st Oct 2025 for contract id 84")
        
        test_message = "update billing prompt date to 1st Oct 2025 for contract id 84"
        
        initial_message = HumanMessage(content=test_message)
        initial_state = create_initial_state(
            user_id="7615479c-2785-4695-853c-1a898d1b7dc5",
            session_id="test-session-real-update-by-id",
            user_name="Test User",
            user_role="admin",
            initial_message=initial_message
        )
        
        try:
            result = await test_executor.invoke(
                initial_state, 
                contract_agent_instance, 
                "contract_agent"
            )
            
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                response = getattr(last_message, 'content', str(last_message))
                print(f"✅ Agent Response: {response}")
                
                # Check if the agent is trying to use the right tool
                if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                    tool_calls = last_message.tool_calls
                    print(f"🔧 Tool calls made: {[tc.function.name for tc in tool_calls]}")
                    
                    # Check if update_contract_by_id is being called
                    if any(tc.function.name == "update_contract_by_id" for tc in tool_calls):
                        print("✅ SUCCESS: Agent correctly identified this as a contract update by ID scenario")
                        print("✅ Agent is calling 'update_contract_by_id' tool")
                    else:
                        print("❌ ISSUE: Agent should call 'update_contract_by_id' but called:", [tc.function.name for tc in tool_calls])
                else:
                    print("❌ ISSUE: Agent didn't make any tool calls")
            else:
                print("❌ ISSUE: No response from agent")
                
        except Exception as e:
            print(f"❌ Error in test 2: {e}")
        
        print("\n" + "=" * 80)
        print("📊 REAL SCENARIO TEST SUMMARY")
        print("=" * 80)
        print("These tests verify that the contract_agent now has the correct tools")
        print("and can identify the right scenarios for:")
        print("1. Creating contracts for new clients (with contact info)")
        print("2. Updating contracts by contract ID")
        print("\nIf the agent is making the correct tool calls, the fixes are working!")
        
    except Exception as e:
        print(f"❌ Real scenario test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Restore original API key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key
        else:
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

if __name__ == "__main__":
    asyncio.run(test_real_scenarios())

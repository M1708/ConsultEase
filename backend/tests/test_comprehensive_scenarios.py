#!/usr/bin/env python3
"""
Comprehensive test suite to verify all scenarios work correctly
and that existing functionality wasn't broken by recent changes.
"""
import asyncio
import os
from src.aiagents.graph.nodes import EnhancedAgentNodeExecutor, contract_agent_instance, client_agent_instance
from src.aiagents.graph.state import create_initial_state
from langchain_core.messages import HumanMessage

async def test_comprehensive_scenarios():
    """Test all scenarios to ensure nothing was broken"""
    
    # Ensure no OpenAI API key is available to test fallback logic
    original_key = os.environ.get("OPENAI_API_KEY")
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    try:
        # Create test executor
        test_executor = EnhancedAgentNodeExecutor()
        
        print("🧪 COMPREHENSIVE SCENARIO TESTING")
        print("=" * 80)
        
        test_results = []
        
        # Test 1: Contract creation for NEW client (critical fix)
        print("\n1️⃣ Testing CONTRACT CREATION for NEW CLIENT...")
        test_message = "create a new contract for client HealthPlus LLC. It's a startup firm with Maria Black as the contact, maria.black@hp.com. The contract starts on 1st Oct 2025 and ends on 31st Mar 2026. It's a fixed contract with original amount of $250,000, billing prompt date is 30th Nov 2025."
        
        result = await run_test(test_executor, test_message, "test-session-new-client-contract", "contract_agent")
        test_results.append(("New Client + Contract Creation", result))
        
        # Test 2: Contract update by ID (critical fix)
        print("\n2️⃣ Testing CONTRACT UPDATE by ID...")
        test_message = "update billing prompt date to 1st Oct 2025 for contract id 84"
        
        result = await run_test(test_executor, test_message, "test-session-update-by-id", "contract_agent")
        test_results.append(("Contract Update by ID", result))
        
        # Test 3: Contract update by client name (existing functionality)
        print("\n3️⃣ Testing CONTRACT UPDATE by CLIENT NAME...")
        test_message = "update billing prompt date to 15th Dec 2025 for Acme Corporation"
        
        result = await run_test(test_executor, test_message, "test-session-update-by-name", "contract_agent")
        test_results.append(("Contract Update by Client Name", result))
        
        # Test 4: Client details retrieval (existing functionality)
        print("\n4️⃣ Testing CLIENT DETAILS RETRIEVAL...")
        test_message = "get client details for TechCorp"
        
        result = await run_test(test_executor, test_message, "test-session-client-details", "client_agent")
        test_results.append(("Client Details Retrieval", result))
        
        # Test 5: Contract retrieval (existing functionality)
        print("\n5️⃣ Testing CONTRACT RETRIEVAL...")
        test_message = "get contracts for Acme Corporation"
        
        result = await run_test(test_executor, test_message, "test-session-contract-retrieval", "contract_agent")
        test_results.append(("Contract Retrieval", result))
        
        # Test 6: All clients retrieval (existing functionality)
        print("\n6️⃣ Testing ALL CLIENTS RETRIEVAL...")
        test_message = "show me all clients"
        
        result = await run_test(test_executor, test_message, "test-session-all-clients", "client_agent")
        test_results.append(("All Clients Retrieval", result))
        
        # Test 7: Contract creation for existing client (existing functionality)
        print("\n7️⃣ Testing CONTRACT CREATION for EXISTING CLIENT...")
        test_message = "create a new contract for TechCorp. It's a fixed contract worth $150,000 starting from 1st Nov 2025 to 30th Apr 2026"
        
        result = await run_test(test_executor, test_message, "test-session-existing-client-contract", "contract_agent")
        test_results.append(("Contract Creation for Existing Client", result))
        
        # Test 8: Client update (existing functionality)
        print("\n8️⃣ Testing CLIENT UPDATE...")
        test_message = "update client TechCorp to change their industry to Technology Services"
        
        result = await run_test(test_executor, test_message, "test-session-client-update", "client_agent")
        test_results.append(("Client Update", result))
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for i, (test_name, passed) in enumerate(test_results, 1):
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{i}. {test_name}: {status}")
            if passed:
                passed_tests += 1
        
        print(f"\n📈 Overall Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! No functionality was broken.")
            print("✅ Critical fixes are working correctly")
            print("✅ Existing functionality is preserved")
        else:
            print(f"\n⚠️ {total_tests - passed_tests} test(s) failed - some functionality may be broken")
        
        return passed_tests == total_tests
        
    except Exception as e:
        print(f"❌ Comprehensive test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original API key if it existed
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

async def run_test(executor, message, session_id, agent_name):
    """Run a single test and return success status"""
    try:
        initial_message = HumanMessage(content=message)
        initial_state = create_initial_state(
            user_id="7615479c-2785-4695-853c-1a898d1b7dc5",
            session_id=session_id,
            user_name="Test User",
            user_role="admin",
            initial_message=initial_message
        )
        
        if agent_name == "contract_agent":
            agent_instance = contract_agent_instance
        else:
            agent_instance = client_agent_instance
        
        result = await executor.invoke(
            initial_state, 
            agent_instance, 
            agent_name
        )
        
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            response = getattr(last_message, 'content', str(last_message))
            print(f"✅ Response: {response[:200]}...")
            
            # Check for success indicators
            success_indicators = [
                "created", "updated", "successfully", "found", "retrieved", 
                "details", "contract", "client", "✅"
            ]
            
            # Check for error indicators
            error_indicators = [
                "error", "failed", "couldn't", "unable", "not found", 
                "invalid", "❌"
            ]
            
            has_success = any(word in response.lower() for word in success_indicators)
            has_error = any(word in response.lower() for word in error_indicators)
            
            # Test passes if it has success indicators and no error indicators
            test_passed = has_success and not has_error
            
            if test_passed:
                print("✅ TEST PASSED")
            else:
                print("❌ TEST FAILED")
                print(f"Full response: {response}")
            
            return test_passed
        else:
            print("❌ TEST FAILED - No response")
            return False
    
    except Exception as e:
        print(f"❌ TEST FAILED - Exception: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_comprehensive_scenarios())
    if success:
        print("\n🎯 All comprehensive tests passed!")
    else:
        print("\n⚠️ Some comprehensive tests failed!")

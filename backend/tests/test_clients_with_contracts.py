"""
Comprehensive test suite for contract functionality
"""
import asyncio
import sys
from pathlib import Path

# Add the backend directory to the python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aiagents.graph.graph import app as agent_app
from src.aiagents.graph.state import create_initial_state
from langchain_core.messages import HumanMessage

async def test_contract_functionality():
    """Test comprehensive contract functionality using existing test data"""
    
    test_cases = [
        {
            "name": "Show all contracts",
            "message": "Show me all contracts",
            "expected_agent": "contract_agent"
        },
        {
            "name": "Show all clients with contracts",
            "message": "Show me all clients with their contracts",
            "expected_agent": "contract_agent"
        },
        {
            "name": "Get contracts for specific client",
            "message": "Show me contracts for TechCorp",
            "expected_agent": "contract_agent"
        },
        {
            "name": "Get contract details",
            "message": "Show me details for contract 1",
            "expected_agent": "contract_agent"
        },
        {
            "name": "Update contract status",
            "message": "Update contract 1 to change the status to completed",
            "expected_agent": "contract_agent"
        },
        {
            "name": "Get contracts by client name alternative",
            "message": "What contracts does Acme Corporation have?",
            "expected_agent": "contract_agent"
        },
        {
            "name": "Contract search query",
            "message": "Find all active contracts",
            "expected_agent": "contract_agent"
        },
        {
            "name": "Contract billing information",
            "message": "Show me billing information for all contracts",
            "expected_agent": "contract_agent"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"🧪 Test {i}/{len(test_cases)}: {test_case['name']}")
        print(f"📝 Message: '{test_case['message']}'")
        print(f"{'='*60}")
        
        try:
            # Create initial state with proper user context
            initial_message = HumanMessage(content=test_case['message'])
            initial_state = create_initial_state(
                user_id="7615479c-2785-4695-853c-1a898d1b7dc5",
                session_id=f"test-session-{i}",
                user_name="Test User",
                user_role="admin",
                initial_message=initial_message
            )
            
            # Add user context to the state for tool execution
            initial_state["context"]["user_id"] = "7615479c-2785-4695-853c-1a898d1b7dc5"
            initial_state["context"]["session_id"] = f"test-session-{i}"
            initial_state["context"]["user_name"] = "Test User"
            initial_state["context"]["role"] = "admin"
            
            # Invoke the graph
            result = await agent_app.ainvoke(initial_state, config={"recursion_limit": 10})
            
            current_agent = result.get('current_agent', 'unknown')
            
            # Check if we have messages
            agent_response = "No response"
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    agent_response = last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    agent_response = last_message['content']
            
            # Determine test result
            agent_correct = current_agent == test_case['expected_agent']
            
            test_result = {
                "name": test_case['name'],
                "message": test_case['message'],
                "expected_agent": test_case['expected_agent'],
                "actual_agent": current_agent,
                "agent_correct": agent_correct,
                "response": agent_response[:200] + "..." if len(agent_response) > 200 else agent_response,
                "success": True
            }
            
            print(f"📊 Current agent: {current_agent}")
            print(f"✅ Expected agent: {test_case['expected_agent']}")
            print(f"🎯 Agent routing: {'✅ CORRECT' if agent_correct else '❌ INCORRECT'}")
            print(f"🤖 Agent response: {test_result['response']}")
            
            results.append(test_result)
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            test_result = {
                "name": test_case['name'],
                "message": test_case['message'],
                "expected_agent": test_case['expected_agent'],
                "actual_agent": "error",
                "agent_correct": False,
                "response": f"Error: {str(e)}",
                "success": False
            }
            results.append(test_result)
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    correct_routing = sum(1 for r in results if r['agent_correct'])
    
    print(f"Total tests: {total_tests}")
    print(f"Successful tests: {successful_tests}/{total_tests}")
    print(f"Correct agent routing: {correct_routing}/{total_tests}")
    
    # Print detailed results
    print(f"\n📋 DETAILED RESULTS:")
    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result['success'] and result['agent_correct'] else "❌ FAIL"
        print(f"{i}. {result['name']}: {status}")
        if not result['agent_correct']:
            print(f"   Expected: {result['expected_agent']}, Got: {result['actual_agent']}")
    
    return results

if __name__ == "__main__":
    print("🧪 Starting comprehensive contract functionality tests...")
    results = asyncio.run(test_contract_functionality())
    
    # Final summary
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'] and r['agent_correct'])
    
    if successful_tests == total_tests:
        print(f"\n🎉 All {total_tests} contract tests passed!")
    else:
        print(f"\n⚠️ {successful_tests}/{total_tests} contract tests passed")

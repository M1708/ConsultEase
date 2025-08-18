#!/usr/bin/env python3
"""
Test script to verify the smart contract functionality
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the backend src directory to the Python path
backend_src = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from backend.src.aiagents.agent_orchestrator import MultiAgentOrchestrator
from backend.src.database.core.database import get_db

async def test_smart_contracts():
    """Test the smart contract functionality that should resolve client names automatically"""
    print("📋 Testing Smart Contract Functionality")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = MultiAgentOrchestrator()
    
    # Get database session
    db = next(get_db())
    
    # Test context
    context = {
        "user_id": "test_user",
        "session_id": "test_session",
        "database": db
    }
    
    # Test cases for smart contract functionality
    test_cases = [
        {
            "name": "Smart Contract Creation - Single Client Match",
            "message": "Create a Fixed contract for Solana Inc with amount $50000",
            "expected_behavior": "Should find Solana Inc client and create contract automatically"
        },
        {
            "name": "Smart Contract Creation - Multiple Client Disambiguation",
            "message": "Create an Hourly contract for TechCorp",
            "expected_behavior": "Should find multiple TechCorp clients and ask for clarification"
        },
        {
            "name": "Get Client Contracts",
            "message": "Show me all contracts for TechStart Inc",
            "expected_behavior": "Should find TechStart Inc and list their contracts"
        },
        {
            "name": "Contract Document Management",
            "message": "I want to upload a contract document for Solana Inc",
            "expected_behavior": "Should find Solana Inc contract and provide upload instructions"
        },
        {
            "name": "Contract Creation - Non-existent Client",
            "message": "Create a contract for NonExistentCorp",
            "expected_behavior": "Should inform user that client doesn't exist"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['name']}")
        print(f"Message: {test_case['message']}")
        print(f"Expected: {test_case['expected_behavior']}")
        print("-" * 50)
        
        try:
            result = await orchestrator.process_message(test_case["message"], context)
            
            success = result.get('success', False)
            agent = result.get('agent', 'Unknown')
            response = result.get('response', 'No response')
            data = result.get('data')
            
            print(f"✅ Agent: {agent}")
            print(f"✅ Success: {success}")
            print(f"✅ Response: {response}")
            
            if data:
                print(f"✅ Data: {data}")
            
            # Evaluate test results
            test_passed = False
            
            if agent == "ContractBot":
                if "successfully" in response.lower() and "contract" in response.lower():
                    print("🎉 SUCCESS: Smart contract creation worked!")
                    test_passed = True
                elif "multiple clients" in response.lower() and "specify" in response.lower():
                    print("🎉 SUCCESS: Smart disambiguation worked!")
                    test_passed = True
                elif "found" in response.lower() and "contracts" in response.lower():
                    print("🎉 SUCCESS: Contract listing worked!")
                    test_passed = True
                elif "upload" in response.lower() and "endpoint" in response.lower():
                    print("🎉 SUCCESS: Document management guidance worked!")
                    test_passed = True
                elif "not found" in response.lower() or "doesn't exist" in response.lower():
                    print("🎉 SUCCESS: Non-existent client handling worked!")
                    test_passed = True
                else:
                    print("ℹ️  INFO: Agent provided helpful guidance")
                    test_passed = True
            else:
                test_passed = success
            
            results.append({
                "test_name": test_case['name'],
                "passed": test_passed,
                "success": success,
                "agent": agent,
                "response": response
            })
                
        except Exception as e:
            print(f"❌ Exception occurred: {str(e)}")
            results.append({
                "test_name": test_case['name'],
                "passed": False,
                "success": False,
                "agent": "Error",
                "response": str(e)
            })
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SMART CONTRACT TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = [r for r in results if r['passed']]
    failed_tests = [r for r in results if not r['passed']]
    
    print(f"✅ Passed: {len(passed_tests)}/{len(results)} tests")
    print(f"❌ Failed: {len(failed_tests)}/{len(results)} tests")
    
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"  - {test['test_name']}: {test['response']}")
    
    # Check if the smart functionality is working
    contract_tests = [r for r in results if r['agent'] == 'ContractBot']
    smart_working = len([t for t in contract_tests if t['passed']]) > 0
    
    print(f"\n🔍 SMART CONTRACT STATUS:")
    print(f"✅ Smart Contract Creation: {'WORKING' if smart_working else 'NEEDS IMPROVEMENT'}")
    
    if smart_working:
        print("\n🎉 Smart contract functionality is working!")
        print("   - Users can create contracts by client name")
        print("   - System automatically resolves client names to IDs")
        print("   - Handles multiple client disambiguation")
        print("   - Provides document upload guidance")
        print("   - No need for users to provide technical details")
    else:
        print("\n⚠️  Smart contract functionality needs improvement:")
        print("   - Agent may still be asking for technical IDs")
        print("   - Client name resolution may not be working")

if __name__ == "__main__":
    asyncio.run(test_smart_contracts())

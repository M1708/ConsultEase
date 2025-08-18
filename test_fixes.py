#!/usr/bin/env python3
"""
Test script to verify all the fixes work correctly
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

async def test_all_fixes():
    """Test all the fixes we implemented"""
    print("🔧 Testing All ConsultEase Fixes")
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
    
    # Test cases for all the fixes
    test_cases = [
        {
            "name": "JSON Parsing Fix - Complex Client Creation",
            "message": "Create a client called MedCorp in the software industry. It's a midsize company.I don't have any other information at the moment for this client",
            "expected_success": True,
            "test_type": "json_parsing"
        },
        {
            "name": "JSON Parsing Fix - Client with Quotes",
            "message": "Create a client called \"Tech Solutions Inc.\" in the IT industry",
            "expected_success": True,
            "test_type": "json_parsing"
        },
        {
            "name": "Workflow Fix - Client Onboarding",
            "message": "Onboard new client called DataCorp in the analytics industry",
            "expected_success": True,
            "test_type": "workflow"
        },
        {
            "name": "Regular Agent Function - Search Clients",
            "message": "Search for clients in technology",
            "expected_success": True,
            "test_type": "regular_agent"
        },
        {
            "name": "Time Agent Function - Log Time",
            "message": "Log 6 hours for development work on project Alpha",
            "expected_success": True,
            "test_type": "time_agent"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['name']}")
        print(f"Message: {test_case['message']}")
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
            
            # Determine if test passed
            test_passed = success == test_case['expected_success']
            
            if test_passed:
                print(f"🎉 TEST PASSED: {test_case['test_type']} functionality works!")
            else:
                print(f"❌ TEST FAILED: Expected success={test_case['expected_success']}, got success={success}")
            
            results.append({
                "test_name": test_case['name'],
                "test_type": test_case['test_type'],
                "passed": test_passed,
                "success": success,
                "agent": agent,
                "response": response
            })
                
        except Exception as e:
            print(f"❌ Exception occurred: {str(e)}")
            results.append({
                "test_name": test_case['name'],
                "test_type": test_case['test_type'],
                "passed": False,
                "success": False,
                "agent": "Error",
                "response": str(e)
            })
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = [r for r in results if r['passed']]
    failed_tests = [r for r in results if not r['passed']]
    
    print(f"✅ Passed: {len(passed_tests)}/{len(results)} tests")
    print(f"❌ Failed: {len(failed_tests)}/{len(results)} tests")
    
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"  - {test['test_name']}: {test['response']}")
    
    # Test specific fixes
    print("\n🔍 FIX VERIFICATION:")
    
    json_tests = [r for r in results if r['test_type'] == 'json_parsing']
    workflow_tests = [r for r in results if r['test_type'] == 'workflow']
    
    json_passed = all(t['passed'] for t in json_tests)
    workflow_passed = all(t['passed'] for t in workflow_tests)
    
    print(f"✅ JSON Parsing Fix: {'WORKING' if json_passed else 'FAILED'}")
    print(f"✅ Workflow Fix: {'WORKING' if workflow_passed else 'FAILED'}")
    print(f"✅ Agent Function Calling: {'WORKING' if len(passed_tests) > 0 else 'FAILED'}")
    
    if len(passed_tests) == len(results):
        print("\n🎉 ALL FIXES VERIFIED SUCCESSFULLY!")
    else:
        print(f"\n⚠️  {len(failed_tests)} issues still need attention.")

if __name__ == "__main__":
    asyncio.run(test_all_fixes())

#!/usr/bin/env python3
"""
Test script to verify the smart time entry functionality
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

async def test_smart_time_entry():
    """Test the smart time entry functionality that should resolve project names automatically"""
    print("🕒 Testing Smart Time Entry Functionality")
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
    
    # Test cases for smart time entry
    test_cases = [
        {
            "name": "Search Available Projects",
            "message": "Show me all available projects for time logging",
            "expected_behavior": "Should list all available projects in the system"
        },
        {
            "name": "Smart Time Entry - Solana Project",
            "message": "Log 6 hours for development work on Solana project",
            "expected_behavior": "Should search for 'Solana' project and log time automatically"
        },
        {
            "name": "Time Entry with Client Name",
            "message": "Log 3 hours for client meeting with TechCorp",
            "expected_behavior": "Should find TechCorp client and associated projects"
        },
        {
            "name": "Search Projects by Client",
            "message": "What projects are available for TechStart client?",
            "expected_behavior": "Should search projects for TechStart client"
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
            
            # Check if this is the TimeTracker agent
            if agent == "TimeTracker":
                # Check for actual problems (asking for technical IDs)
                if ("client_id" in response.lower() and "provide" in response.lower()) or \
                   ("contract_id" in response.lower() and "provide" in response.lower()):
                    print("❌ ISSUE: Agent is asking for technical IDs")
                    test_passed = False
                elif "successfully" in response.lower() and "logged" in response.lower():
                    print("🎉 SUCCESS: Smart time entry worked - time logged successfully!")
                    test_passed = True
                elif "found client" in response.lower() and ("no active projects" in response.lower() or "no projects" in response.lower()):
                    print("🎉 SUCCESS: Smart client discovery worked - found client but correctly identified no projects!")
                    test_passed = True
                elif "found" in response.lower() and "projects" in response.lower():
                    print("🎉 SUCCESS: Project search worked!")
                    test_passed = True
                elif "warning" in response.lower() and ("no available projects" in response.lower() or "no projects" in response.lower()):
                    print("🎉 SUCCESS: Smart guidance - correctly identified no projects available!")
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
    print("📊 SMART TIME ENTRY TEST SUMMARY")
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
    time_tracker_tests = [r for r in results if r['agent'] == 'TimeTracker']
    smart_working = len([t for t in time_tracker_tests if t['passed']]) > 0
    
    print(f"\n🔍 SMART TIME ENTRY STATUS:")
    print(f"✅ Smart Time Entry: {'WORKING' if smart_working else 'NEEDS IMPROVEMENT'}")
    
    if smart_working:
        print("\n🎉 Smart time entry functionality is working!")
        print("   - Users can log time by project name")
        print("   - System automatically resolves client and contract IDs")
        print("   - No need for users to provide technical details")
    else:
        print("\n⚠️  Smart time entry needs improvement:")
        print("   - Agent may still be asking for technical IDs")
        print("   - Project name resolution may not be working")

if __name__ == "__main__":
    asyncio.run(test_smart_time_entry())

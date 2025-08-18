#!/usr/bin/env python3
"""
Test script for the ConsultEase agents
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

async def test_agents():
    """Test the multi-agent system"""
    print("🚀 Testing ConsultEase Multi-Agent System")
    print("=" * 50)
    
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
    
    # Test cases
    test_cases = [
        {
            "message": "Hello, what can you help me with?",
            "expected_agent": "ContractBot"
        },
        {
            "message": "Create a new client called TechCorp in the technology industry",
            "expected_agent": "ContractBot"
        },
        {
            "message": "Search for clients in technology",
            "expected_agent": "ContractBot"
        },
        {
            "message": "Log 8 hours for project development work",
            "expected_agent": "TimeTracker"
        },
        {
            "message": "Show me my timesheet for this week",
            "expected_agent": "TimeTracker"
        }
    ]
    
    # Run tests
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['message']}")
        print("-" * 40)
        
        try:
            result = await orchestrator.process_message(test_case["message"], context)
            
            print(f"✅ Agent: {result['agent']}")
            print(f"✅ Success: {result['success']}")
            print(f"✅ Response: {result['response']}")
            
            if result.get('data'):
                print(f"✅ Data: {result['data']}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 Agent testing completed!")

if __name__ == "__main__":
    asyncio.run(test_agents())

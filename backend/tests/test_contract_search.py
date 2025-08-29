#!/usr/bin/env python3
"""
Test the new contract search functionality
"""
import asyncio
from src.aiagents.graph.graph import app as agent_app
from src.aiagents.graph.state import create_initial_state
from langchain_core.messages import HumanMessage
from src.database.core.database import get_db

async def test_contract_search():
    """Test contract search for monthly billing"""
    print("🎯 TESTING CONTRACT SEARCH FUNCTIONALITY")
    print("=" * 80)
    
    # Test message for searching contracts with monthly billing
    test_message = "show me all contracts with monthly billing"
    
    print(f"User message: '{test_message}'")
    print()
    
    # Create initial state
    initial_message = HumanMessage(content=test_message)
    initial_state = create_initial_state(
        user_id="test_user_123",
        session_id="test_session_456",
        user_name="Test User",
        user_role="admin",
        initial_message=initial_message
    )
    
    # Add database to context
    db = next(get_db())
    initial_state["context"]["database"] = db
    
    try:
        print("🚀 Invoking agent graph...")
        result = await agent_app.ainvoke(initial_state, config={"recursion_limit": 10})
        
        # Extract the response
        response_content = "No response generated"
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                response_content = last_message.content
            elif isinstance(last_message, dict) and 'content' in last_message:
                response_content = last_message['content']
        
        print("🤖 Agent Response:")
        print("-" * 40)
        print(response_content)
        print("-" * 40)
        
        # Check if the response indicates successful search
        if "monthly" in response_content.lower() and ("contract" in response_content.lower() or "found" in response_content.lower()):
            print("✅ SUCCESS: Agent successfully processed contract search request!")
        else:
            print("❌ ISSUE: Agent response doesn't seem to indicate successful contract search")
        
        print(f"\n📊 Agent Status: {result.get('status', 'unknown')}")
        print(f"📊 Processing Times: {result.get('agent_response_times', {})}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_contract_search())

#!/usr/bin/env python3
"""
Debug script for LangGraph unhashable type error
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

async def test_minimal_langgraph():
    """Test minimal LangGraph setup to isolate the unhashable type error"""
    try:
        print("🔍 Testing minimal LangGraph setup...")

        # Import minimal components
        from aiagents.graph.state import AgentState
        from langgraph.graph import StateGraph, END

        # Create minimal state
        minimal_state = {
            "messages": [{"type": "user", "content": "Hello", "role": "user"}],
            "current_agent": "router",
            "data": {},
            "status": "routing"
        }

        print(f"✅ Minimal state created: {list(minimal_state.keys())}")

        # Test StateGraph creation
        workflow = StateGraph(AgentState)
        print("✅ StateGraph created successfully")

        # Add a simple node
        def simple_node(state):
            return {"messages": [{"content": "Hello from simple node", "role": "assistant"}]}

        workflow.add_node("simple", simple_node)
        workflow.set_entry_point("simple")
        workflow.add_edge("simple", END)

        print("✅ Simple node added")

        # Compile the graph
        app = workflow.compile()
        print("✅ Graph compiled successfully")

        # Test invocation
        result = await app.ainvoke(minimal_state, config={"recursion_limit": 5})
        print(f"✅ Minimal graph invocation successful: {result}")

        return True

    except Exception as e:
        print(f"❌ Minimal test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_langgraph():
    """Test the full LangGraph setup"""
    try:
        print("🔍 Testing full LangGraph setup...")

        # Import full components
        from aiagents.graph.hybrid_workflow import app as agent_app
        from aiagents.graph.state import create_initial_state

        # Create initial state
        initial_state = create_initial_state(
            user_id="test_user",
            session_id="test_session",
            user_name="Test User",
            user_role="admin",
            initial_message={"type": "user", "content": "Hello", "role": "user"}
        )

        print(f"✅ Full initial state created: {list(initial_state.keys())}")

        # Test invocation with minimal recursion
        result = await agent_app.ainvoke(initial_state, config={"recursion_limit": 3})
        print(f"✅ Full graph invocation successful: {result}")

        return True

    except Exception as e:
        print(f"❌ Full test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def debug_state_structure():
    """Debug the state structure to find unhashable types"""
    try:
        print("🔍 Debugging state structure...")

        from aiagents.graph.state import create_initial_state

        # Create initial state
        initial_state = create_initial_state(
            user_id="test_user",
            session_id="test_session",
            user_name="Test User",
            user_role="admin",
            initial_message={"type": "user", "content": "Hello", "role": "user"}
        )

        print("🔍 Checking state for unhashable types...")

        def check_hashable(obj, path="root", depth=0):
            """Recursively check for unhashable types"""
            if depth > 10:
                return

            try:
                hash(obj)
                print(f"✅ Hashable: {path} =

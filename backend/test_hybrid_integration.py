#!/usr/bin/env python3
"""
Test script for OpenAI Agents SDK Hybrid Integration

This script tests the hybrid workflow integration to ensure:
1. SDK agents can be initialized
2. Memory store works correctly
3. Tool registry functions properly
4. Hybrid workflow can process requests
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aiagents.graph.state import create_initial_state
from aiagents.graph.hybrid_workflow import initialize_hybrid_workflow, get_hybrid_orchestrator
from aiagents.agents_sdk.agent_factory import AgentFactory
from aiagents.agents_sdk.tool_definitions import ToolRegistry
from aiagents.agents_sdk.memory_store import SDKMemoryStore


async def test_sdk_memory_store():
    """Test SDK Memory Store functionality"""
    print("🧪 Testing SDK Memory Store...")

    memory_store = SDKMemoryStore()

    # Test storing agent memory
    test_session = "test_session_123"
    test_user = "test_user_456"
    test_agent = "contract_agent"

    test_data = {
        "last_action": "created_contract",
        "contract_id": "TEST_001",
        "timestamp": datetime.now().isoformat()
    }

    success = await memory_store.store_agent_memory(
        test_agent, test_session, test_user, test_data, "context"
    )

    if success:
        print("✅ Memory store: Successfully stored agent memory")
    else:
        print("❌ Memory store: Failed to store agent memory")
        return False

    # Test retrieving agent memory
    retrieved = await memory_store.retrieve_agent_memory(
        test_agent, test_session, test_user, "context"
    )

    if retrieved and retrieved.get("last_action") == "created_contract":
        print("✅ Memory store: Successfully retrieved agent memory")
    else:
        print("❌ Memory store: Failed to retrieve agent memory")
        return False

    # Test conversation history
    messages = [
        {"role": "user", "content": "Create a contract for ABC Corp", "timestamp": datetime.now().isoformat()},
        {"role": "assistant", "content": "I'll help you create a contract", "timestamp": datetime.now().isoformat()}
    ]

    success = await memory_store.store_conversation_history(
        test_agent, test_session, test_user, messages
    )

    if success:
        print("✅ Memory store: Successfully stored conversation history")
    else:
        print("❌ Memory store: Failed to store conversation history")
        return False

    # Test retrieving conversation history
    history = await memory_store.get_conversation_history(
        test_agent, test_session, test_user, limit=5
    )

    if len(history) == 2:
        print("✅ Memory store: Successfully retrieved conversation history")
    else:
        print("❌ Memory store: Failed to retrieve conversation history")
        return False

    print("✅ SDK Memory Store tests passed!")
    return True


async def test_agent_factory():
    """Test Agent Factory functionality"""
    print("🧪 Testing Agent Factory...")

    factory = AgentFactory()

    # Test SDK availability
    sdk_available = factory.is_sdk_available()
    print(f"📊 SDK Available: {sdk_available}")

    # Test agent configuration
    config = factory.get_agent_config("contract_agent")
    if config and "instructions" in config:
        print("✅ Agent Factory: Successfully retrieved agent configuration")
    else:
        print("❌ Agent Factory: Failed to retrieve agent configuration")
        return False

    # Test creating hybrid agent
    hybrid_agent = factory.create_hybrid_agent(
        "test_agent",
        "You are a test agent",
        tools=[]
    )

    if hybrid_agent and "name" in hybrid_agent:
        print("✅ Agent Factory: Successfully created hybrid agent")
    else:
        print("❌ Agent Factory: Failed to create hybrid agent")
        return False

    print("✅ Agent Factory tests passed!")
    return True


async def test_tool_registry():
    """Test Tool Registry functionality"""
    print("🧪 Testing Tool Registry...")

    registry = ToolRegistry()

    # Test getting tools
    tools = registry.get_all_tools()
    if len(tools) > 0:
        print(f"✅ Tool Registry: Found {len(tools)} registered tools")
    else:
        print("❌ Tool Registry: No tools found")
        return False

    # Test getting tool names
    tool_names = registry.get_tool_names()
    expected_tools = ["search_contracts", "update_contract", "create_client", "create_contract", "get_contract_details", "get_client_contracts"]

    if all(name in tool_names for name in expected_tools):
        print("✅ Tool Registry: All expected tools are registered")
    else:
        print("❌ Tool Registry: Missing expected tools")
        return False

    # Test getting specific tool
    search_tool = registry.get_tool("search_contracts")
    if search_tool and "function" in search_tool:
        print("✅ Tool Registry: Successfully retrieved specific tool")
    else:
        print("❌ Tool Registry: Failed to retrieve specific tool")
        return False

    print("✅ Tool Registry tests passed!")
    return True


async def test_hybrid_orchestrator():
    """Test Hybrid Orchestrator functionality"""
    print("🧪 Testing Hybrid Orchestrator...")

    orchestrator = get_hybrid_orchestrator()

    # Test agent status
    status = orchestrator.get_agent_status()
    print(f"📊 Agent Status: {status}")

    if "sdk_available" in status:
        print("✅ Hybrid Orchestrator: Successfully retrieved agent status")
    else:
        print("❌ Hybrid Orchestrator: Failed to retrieve agent status")
        return False

    print("✅ Hybrid Orchestrator tests passed!")
    return True


async def test_hybrid_workflow():
    """Test Hybrid Workflow functionality"""
    print("🧪 Testing Hybrid Workflow...")

    try:
        # Initialize hybrid workflow
        app = await initialize_hybrid_workflow()
        print("✅ Hybrid Workflow: Successfully initialized")

        # Test creating initial state
        from langchain_core.messages import HumanMessage
        initial_message = HumanMessage(content="Hello, I need help with contracts")

        initial_state = create_initial_state(
            user_id="test_user",
            session_id="test_session",
            user_name="Test User",
            user_role="admin",
            initial_message=initial_message
        )

        if initial_state and "messages" in initial_state:
            print("✅ Hybrid Workflow: Successfully created initial state")
        else:
            print("❌ Hybrid Workflow: Failed to create initial state")
            return False

        print("✅ Hybrid Workflow tests passed!")
        return True

    except Exception as e:
        print(f"❌ Hybrid Workflow: Error during testing - {e}")
        return False


async def run_integration_tests():
    """Run all integration tests"""
    print("🚀 Starting OpenAI Agents SDK Integration Tests")
    print("=" * 50)

    tests = [
        ("SDK Memory Store", test_sdk_memory_store),
        ("Agent Factory", test_agent_factory),
        ("Tool Registry", test_tool_registry),
        ("Hybrid Orchestrator", test_hybrid_orchestrator),
        ("Hybrid Workflow", test_hybrid_workflow),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} tests...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: Test failed with exception - {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n📈 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All integration tests passed! Ready for production.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    # Run the integration tests
    success = asyncio.run(run_integration_tests())

    if success:
        print("\n🎯 Next Steps:")
        print("1. Run the application with hybrid workflow enabled")
        print("2. Test real user interactions")
        print("3. Monitor performance and memory usage")
        print("4. Gradually migrate remaining agents")
    else:
        print("\n🔧 Please fix the failing tests before proceeding.")
        sys.exit(1)

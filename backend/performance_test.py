"""
Simple performance test script for agent latency
"""
import asyncio
import time
from src.aiagents.agent_orchestrator import MultiAgentOrchestrator

async def test_agent_performance():
    """Test agent response times"""
    orchestrator = MultiAgentOrchestrator()
    
    test_messages = [
        "Create a new client called Test Corp in Technology industry",
        "Find all contracts for Acme Corp",
        "Log 5 hours of work for Project Alpha today",
        "Create a deliverable for Test Corp called Website Development"
    ]
    
    print("🚀 Starting Agent Performance Test...")
    print("=" * 50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 Test {i}: {message}")
        
        start_time = time.time()
        try:
            context = {
                "user_id": "test-user-123",
                "session_id": "test-session",
                "timestamp": time.time(),
                "user_role": "admin",
                "user_name": "Test User"
            }
            
            result = await orchestrator.process_message(message, context)
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            
            print(f"⏱️  Response Time: {latency:.2f}ms")
            print(f"🤖 Agent: {result.get('agent', 'Unknown')}")
            print(f"✅ Success: {result.get('success', False)}")
            print(f"📄 Response: {result.get('response', 'No response')[:100]}...")
            
        except Exception as e:
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            print(f"❌ Error after {latency:.2f}ms: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🏁 Performance Test Complete")

if __name__ == "__main__":
    asyncio.run(test_agent_performance())

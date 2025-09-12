import asyncio
from src.aiagents.graph.nodes import ContractAgentNode

async def test_deletion_detection():
    try:
        print("=== Testing Deletion Detection ===\n")
        
        # Create the node
        node = ContractAgentNode()
        
        # Test message
        user_message = "delete contract for client InnovateTech Solutions"
        print(f"User message: '{user_message}'")
        
        # Test the fallback detection
        result = await node._fallback_tool_selection(user_message)
        print(f"Selected tool: {result.get('tool_name', 'None')}")
        print(f"Tool args: {result.get('tool_args', {})}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_deletion_detection())
print(f'\nTest result: {result}')

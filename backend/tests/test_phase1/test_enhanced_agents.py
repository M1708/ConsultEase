"""
Test enhanced agent functionality with memory integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.aiagents.graph.state import AgentState, create_initial_state
from src.aiagents.client_agent import ClientAgent
from src.aiagents.memory.conversation_memory import ConversationMemoryManager
from src.aiagents.memory.context_manager import ContextManager
from src.aiagents.graph.nodes import EnhancedAgentNodeExecutor


class TestEnhancedAgents:
    """Test suite for enhanced agent functionality"""
    
    @pytest.fixture
    def sample_state(self):
        """Create a sample agent state for testing"""
        from langchain_core.messages import HumanMessage
        
        initial_message = HumanMessage(content="Create a new client called TechCorp")
        return create_initial_state(
            user_id="test-user-123",
            session_id="test-session-456", 
            user_name="Test User",
            user_role="admin",
            initial_message=initial_message
        )
    
    @pytest.fixture
    def client_agent(self):
        """Create a client agent instance for testing"""
        return ClientAgent()
    
    @pytest.fixture
    def memory_manager(self):
        """Create a memory manager instance for testing"""
        return ConversationMemoryManager()
    
    @pytest.fixture
    def context_manager(self):
        """Create a context manager instance for testing"""
        return ContextManager()
    
    def test_client_agent_initialization(self, client_agent):
        """Test that client agent initializes correctly with memory components"""
        assert client_agent.instructions is not None
        assert client_agent.tools is not None
        assert hasattr(client_agent, 'memory_manager')
        assert hasattr(client_agent, 'context_manager')
        assert len(client_agent.tools) > 0
    
    @pytest.mark.asyncio
    async def test_enhanced_instructions(self, client_agent, sample_state):
        """Test that enhanced instructions include memory context"""
        with patch.object(client_agent.context_manager, 'get_enhanced_context') as mock_context:
            with patch.object(client_agent.memory_manager, 'get_user_preferences_summary') as mock_prefs:
                mock_context.return_value = "Test context"
                mock_prefs.return_value = "Test preferences"
                
                enhanced_instructions = await client_agent.get_enhanced_instructions(sample_state)
                
                assert "Test context" in enhanced_instructions
                assert "Test preferences" in enhanced_instructions
                assert "MEMORY-ENHANCED BEHAVIOR" in enhanced_instructions
                mock_context.assert_called_once()
                mock_prefs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_memory_manager_store_retrieve(self, memory_manager):
        """Test memory storage and retrieval functionality"""
        session_id = "test-session"
        user_id = "test-user"
        
        # Mock Redis client
        with patch.object(memory_manager.session_manager, 'redis_client') as mock_redis:
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = '{"conversation_history": [], "user_preferences": {}, "context_summary": "test", "previous_tasks": [], "learned_patterns": {}}'
            
            # Test storing memory
            from src.aiagents.graph.state import AgentMemory
            test_memory = AgentMemory(
                conversation_history=[{"role": "user", "content": "test message"}],
                user_preferences={"style": "formal"},
                context_summary="Test conversation",
                previous_tasks=[],
                learned_patterns={}
            )
            
            result = await memory_manager.store_conversation_memory(session_id, user_id, test_memory)
            assert result is True
            
            # Test retrieving memory
            retrieved_memory = await memory_manager.retrieve_conversation_memory(session_id, user_id)
            assert retrieved_memory is not None
            assert retrieved_memory["context_summary"] == "test"
    
    @pytest.mark.asyncio
    async def test_context_manager_intent_extraction(self, context_manager):
        """Test intent extraction functionality"""
        test_messages = [
            "Create a new client called TechCorp",
            "Update the contract for existing client",
            "Search for employees in HR department",
            "Delete the old timesheet entries"
        ]
        
        expected_intents = ["create", "update", "retrieve", "delete"]
        
        for message, expected_intent in zip(test_messages, expected_intents):
            intent_data = context_manager.extract_user_intent(message)
            assert intent_data["primary_intent"] == expected_intent
            assert isinstance(intent_data["entities"], list)
            assert intent_data["urgency"] in ["low", "normal", "high"]
    
    @pytest.mark.asyncio
    async def test_enhanced_agent_executor(self, sample_state, client_agent):
        """Test enhanced agent node executor"""
        executor = EnhancedAgentNodeExecutor()
        
        # Mock OpenAI client
        with patch.object(executor, 'client') as mock_client:
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Test response"
            mock_response.choices[0].message.tool_calls = None
            
            mock_client.chat.completions.create.return_value = mock_response
            
            # Mock memory manager
            with patch.object(executor.memory_manager, 'update_conversation_history') as mock_update:
                mock_update.return_value = True
                
                result = await executor.invoke(sample_state, client_agent, "client_agent")
                
                assert "messages" in result
                assert len(result["messages"]) == 1
                assert result["messages"][0].content == "Test response"
                
                # Verify memory was updated
                mock_update.assert_called_once()
    
    def test_agent_state_creation(self):
        """Test agent state creation with all required fields"""
        from langchain_core.messages import HumanMessage
        
        message = HumanMessage(content="Test message")
        state = create_initial_state(
            user_id="user123",
            session_id="session456", 
            user_name="John Doe",
            user_role="manager",
            initial_message=message
        )
        
        # Verify all required fields are present
        assert state["context"]["user_id"] == "user123"
        assert state["context"]["session_id"] == "session456"
        assert state["context"]["user_name"] == "John Doe"
        assert state["context"]["user_role"] == "manager"
        assert state["current_agent"] == "router"
        assert state["status"] == "routing"
        assert len(state["messages"]) == 1
        assert "memory" in state
        assert "error_recovery" in state
        assert "active_agents" in state
    
    @pytest.mark.asyncio
    async def test_conversation_history_update(self, memory_manager):
        """Test conversation history update functionality"""
        session_id = "test-session"
        user_id = "test-user"
        
        with patch.object(memory_manager.session_manager, 'redis_client') as mock_redis:
            # Mock existing memory
            existing_memory = {
                "conversation_history": [{"role": "user", "content": "previous message"}],
                "user_preferences": {},
                "context_summary": "",
                "previous_tasks": [],
                "learned_patterns": {}
            }
            mock_redis.get.return_value = '{"conversation_history": [{"role": "user", "content": "previous message"}], "user_preferences": {}, "context_summary": "", "previous_tasks": [], "learned_patterns": {}}'
            mock_redis.setex.return_value = True
            
            # Add new message
            new_message = {"role": "user", "content": "new message"}
            result = await memory_manager.update_conversation_history(session_id, user_id, new_message)
            
            assert result is True
            mock_redis.setex.assert_called_once()
    
    def test_agent_tool_schemas(self, client_agent):
        """Test that agent tool schemas are properly defined"""
        tools = client_agent.tools
        
        assert len(tools) > 0
        
        for tool in tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
            
            # Verify parameters structure
            params = tool["function"]["parameters"]
            assert "type" in params
            assert params["type"] == "object"
            assert "properties" in params
    
    @pytest.mark.asyncio
    async def test_error_handling_in_enhanced_execution(self, sample_state, client_agent):
        """Test error handling in enhanced agent execution"""
        executor = EnhancedAgentNodeExecutor()
        
        # Mock OpenAI client to raise an exception
        with patch.object(executor, 'client') as mock_client:
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            
            # Should fallback to basic execution
            with patch.object(executor, 'basic_invoke') as mock_basic:
                mock_basic.return_value = {"messages": [Mock()]}
                
                result = await executor.invoke(sample_state, client_agent, "client_agent")
                
                assert "messages" in result
                mock_basic.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])

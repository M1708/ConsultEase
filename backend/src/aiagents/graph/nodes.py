from __future__ import annotations
import os
import json
import time
import asyncio
import re
from openai import OpenAI
from typing import Dict, Any, List, Optional
from datetime import datetime

from .state import AgentState
from .context_extractor import context_extractor
from ..memory.conversation_memory import ConversationMemoryManager
from ..memory.context_manager import ContextManager
from ..orchestration.dynamic_prompts import get_dynamic_instructions, PromptTemplate
from ..orchestration.parallel_executor import ParallelAgentExecutor, ExecutionPlan, ExecutionMode
from ..performance.intelligent_cache import get_cached, set_cached

# Import agent classes to get their tool schemas
from ..contract_agent import ContractAgent
from ..employee_agent import EmployeeAgent
from ..client_agent import ClientAgent
from ..deliverable_agent import DeliverableAgent
from ..time_agent import TimeTrackerAgent
from ..user_agent import UserAgent


class EnhancedAgentNodeExecutor:
    """
    Phase 2 Enhanced Agent Node Executor

    Features:
    - Dynamic context-aware prompts
    - Intelligent caching for performance
    - Parallel execution support
    - Advanced memory integration
    - Sub-100ms response optimization
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            print("Warning: OpenAI API key not found. Agent executor will use fallback mode.")
        self.model = model
        self.memory_manager = ConversationMemoryManager()
        self.context_manager = ContextManager()
        self.parallel_executor = ParallelAgentExecutor()

        # Agent type mapping for dynamic prompts
        self.agent_prompt_mapping = {
            "client_agent": PromptTemplate.CLIENT_AGENT,
            "contract_agent": PromptTemplate.CONTRACT_AGENT,
            "employee_agent": PromptTemplate.EMPLOYEE_AGENT,
            "deliverable_agent": PromptTemplate.DELIVERABLE_AGENT,
            "time_agent": PromptTemplate.TIME_AGENT,
            "user_agent": PromptTemplate.USER_AGENT,
        }

    async def invoke(
        self,
        state: AgentState,
        agent_instance,
        agent_name: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """Phase 2 Enhanced invocation with dynamic prompts and intelligent caching."""
        """
        Phase 2 Enhanced invocation with dynamic prompts and intelligent caching.

        Performance target: <200ms total execution time
        """
        start_time = time.perf_counter()

        # Track invocations to debug recursion
        if not hasattr(self, '_invocation_count'):
            self._invocation_count = 0
        self._invocation_count += 1
        print(f"🔍 DEBUG: {agent_name} invocation #{self._invocation_count}")

        try:
            # 🚀 PERFORMANCE OPTIMIZATION: Track agent execution for contract search optimization

            # Generate cache key for potential response caching
            cache_key = self._generate_cache_key(state, agent_name)

            # Check cache for recent similar requests (optional optimization)
            cached_response = await get_cached(cache_key)
            if cached_response and self._is_cache_valid(cached_response, state):
                print(f"⚡ Cache hit for {agent_name}")
                return cached_response

            # Get dynamic, context-aware instructions
            system_prompt = await self._get_dynamic_instructions(
                agent_name, state, execution_context
            )
            

            print(f"🚀 Invoking {agent_name} with Phase 2 dynamic context...")

            # Prepare messages with optimized structure
            prepared_messages = await self._prepare_messages_optimized(
                state, system_prompt
            )



            # Always extract context from user messages to preserve conversation context
            # This ensures the agent knows what operation to perform
            await self._extract_and_save_context(state, prepared_messages, None)

            # If we have a contract ID but no client name, look up the contract to get the client name
            if (state.get('data', {}).get('current_contract_id') and
                not state.get('data', {}).get('current_client')):
                await self._lookup_contract_and_save_client_name(state)

            # SHORT-CIRCUIT: If we have all context needed, bypass LLM and call tool directly
            if await self._should_short_circuit(state, agent_name):
                return await self._execute_direct_tool_call(state, agent_name)

            # Execute with performance monitoring
            response = await self._execute_with_monitoring(
                prepared_messages, agent_instance.tools, agent_name
            )

            response_message = response.choices[0].message
            print(f"🔍 DEBUG: OpenAI API response received")
            print(f"🔍 DEBUG: OpenAI response message type: {type(response_message)}")
            print(f"🔍 DEBUG: OpenAI response has tool_calls: {hasattr(response_message, 'tool_calls') and response_message.tool_calls}")
            print(f"🔍 DEBUG: OpenAI response content preview: {getattr(response_message, 'content', 'No content')[:100] if getattr(response_message, 'content', None) else 'None'}")

            # DEBUG: Show current state after context extraction
            print(f"🔍 DEBUG: State after context extraction:")
            print(f"🔍 DEBUG: state['data'] = {state.get('data', {})}")

            # TODO: DEBUG - Debug tool calls to track recursion issue
            if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
                print(f"🔍 DEBUG: Agent made {len(response_message.tool_calls)} tool calls:")
                for i, tool_call in enumerate(response_message.tool_calls):
                    print(f"🔍 DEBUG: Tool call {i}: {tool_call.function.name} with args: {tool_call.function.arguments}")
            else:
                print(f"🔍 DEBUG: Agent made no tool calls, response: {response_message.content[:100]}...")

            # Prepare result with serializable message
            if hasattr(response_message, 'content'):
                serializable_message = {
                    "type": "ai",
                    "content": response_message.content,
                    "role": getattr(response_message, 'role', 'assistant')
                }
            else:
                serializable_message = {
                    "type": "ai",
                    "content": str(response_message),
                    "role": "assistant"
                }
                
            # Add tool calls to serializable message if they exist
            if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
                serializable_message["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in response_message.tool_calls
                ]
                print(f"🔍 DEBUG: Stored {len(serializable_message['tool_calls'])} tool calls in serializable message")

            # Update performance tracking
            processing_time = time.perf_counter() - start_time
            await self._update_performance_metrics(
                state, agent_name, processing_time, start_time
            )

            # Update conversation memory asynchronously for better performance
            if response_message.content:
                # For tests, update synchronously to ensure mocks work properly
                try:
                    await self._update_memory_async(
                        state, response_message, agent_name, processing_time
                    )
                except Exception as e:
                    # If async update fails, create task as fallback
                    print(f"Sync memory update failed, using async task: {e}")
                    asyncio.create_task(self._update_memory_async(
                        state, response_message, agent_name, processing_time
                    ))

            print(f"🔍 DEBUG: Final serializable message: {serializable_message}")

            result = {"messages": [serializable_message]}
            print(f"🔍 DEBUG: Agent invoke returning - result = {result}")
            print(f"🔍 DEBUG: Agent invoke returning - state['data'] = {state.get('data', {})}")
            print(f"🔍 DEBUG: Agent invoke returning - user_operation = {state.get('data', {}).get('user_operation', 'NOT_FOUND')}")

            # Cache successful responses (with TTL based on content type)
            if processing_time < 1.0:  # Only cache fast responses
                cache_ttl = self._determine_cache_ttl(serializable_message["content"])
                await set_cached(cache_key, result, cache_ttl)

            print(f"🔍 DEBUG: Agent invoke returning - state['data'] = {state.get('data', {})}")
            print(f"🔍 DEBUG: Agent invoke returning - user_operation = {state.get('data', {}).get('user_operation', 'NOT_FOUND')}")
            return result

        except Exception as e:
            # Only print error if it's not the expected fallback mode message
            if "OpenAI client not available" not in str(e):
                print(f"Error in Phase 2 agent execution: {e}")

            # Fallback to basic execution with error tracking
            processing_time = time.perf_counter() - start_time
            await self._track_error(state, agent_name, str(e), processing_time)

            # Ensure we have the required attributes for basic_invoke
            try:
                instructions = getattr(agent_instance, 'instructions', f"You are {agent_name}, an AI assistant.")
                tools = getattr(agent_instance, 'tools', [])
                return await self.basic_invoke(state, instructions, tools)
            except Exception as fallback_error:
                print(f"Fallback execution also failed: {fallback_error}")
                # Return minimal response to prevent complete failure
                return {"messages": [{"role": "assistant", "content": f"I encountered an error processing your request. Error: {str(e)}"}]}

    async def invoke_parallel(
        self,
        execution_plan: ExecutionPlan,
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> List[Dict]:
        """
        Execute multiple agents in parallel for complex workflows.

        Performance target: Reduce total execution time by 60-80% for parallel tasks
        """
        print(f"🔄 Executing parallel workflow with {len(execution_plan.agents)} agents...")

        # Execute using the parallel executor
        results = await self.parallel_executor.execute_parallel(
            execution_plan, state, agent_registry
        )

        # Convert results to expected format
        formatted_results = []
        for result in results:
            if result.success:
                formatted_results.append({
                    "agent_name": result.agent_name,
                    "messages": [result.result] if result.result else [],
                    "execution_time": result.execution_time
                })
            else:
                formatted_results.append({
                    "agent_name": result.agent_name,
                    "error": result.error,
                    "execution_time": result.execution_time
                })

        return formatted_results

    async def _get_dynamic_instructions(
        self,
        agent_name: str,
        state: AgentState,
        execution_context: Optional[Dict[str, Any]]
    ) -> str:
        """Get dynamic, context-aware instructions for the agent."""

        # Map agent name to prompt template
        prompt_template = self.agent_prompt_mapping.get(agent_name)
        if not prompt_template:
            # Fallback to static instructions
            return f"You are {agent_name}, an AI assistant."

        # Generate dynamic instructions
        try:
            dynamic_instructions = await get_dynamic_instructions(
                prompt_template, state, execution_context
            )
            return dynamic_instructions
        except Exception as e:
            print(f"Error generating dynamic instructions: {e}")
            # Fallback to basic template
            return f"You are Milo, a {agent_name.replace('_', ' ')} specialist."

    async def _prepare_messages_optimized(
        self,
        state: AgentState,
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """Prepare messages with performance optimizations."""

        # Build system prompt with context information
        full_system_prompt = system_prompt

        # Add context information if available
        if 'context' in state and state['context']:
            context_info = []
            if 'file_info' in state['context']:
                file_info = state['context']['file_info']
                context_info.append(f"File attached: {file_info.get('filename', 'unknown')} ({file_info.get('file_size', 0)} bytes)")
                context_info.append(f"File type: {file_info.get('mime_type', 'unknown')}")
                context_info.append(f"File data available: {'Yes' if file_info.get('file_data') else 'No'}")

                # CRITICAL: Tell agent that file data is available (tool wrapper will handle the actual data)
                if file_info.get('file_data'):
                    context_info.append(f"FILE_DATA_AVAILABLE: Yes - Tool wrapper will access the real data")
                    context_info.append(f"FILENAME: {file_info.get('filename')}")
                    context_info.append(f"FILE_SIZE: {file_info.get('file_size')}")
                    context_info.append(f"MIME_TYPE: {file_info.get('mime_type')}")
                    context_info.append(f"INSTRUCTION: Use placeholder '<base64_encoded_data>' - tool wrapper will replace with real data")

                print(f"🔍 DEBUG: File info in context: {file_info.get('filename')}")
                print(f"🔍 DEBUG: File data length in context: {len(file_info.get('file_data', ''))}")

            if context_info:
                context_message = "\n\nContext information:\n" + "\n".join(context_info)
                full_system_prompt += context_message

        prepared_messages = [
            {"role": "system", "content": full_system_prompt}
        ]

        messages = state['messages']

        # CRITICAL FIX: We need to preserve the original user message that contains employee names
        # The issue is that we're only seeing tool call messages, but we need the original user input

        # First, check if we have the original user message in the context
        original_user_message = None
        if 'context' in state and 'original_message' in state['context']:
            original_user_message = state['context']['original_message']
            print(f"🔍 DEBUG: Found original message in context: {original_user_message[:100]}...")

        # If we have an original user message, include it first
        if original_user_message:
            prepared_messages.append({"role": "user", "content": original_user_message})
            print(f"🔍 DEBUG: Added original user message: {original_user_message[:100]}...")

        # Process messages and ensure we capture both user messages and tool results
        print(f"🔍 DEBUG: Processing {len(messages)} messages")
        for i, msg in enumerate(messages):
            print(f"🔍 DEBUG: Raw message {i}: type={type(msg)}, hasattr(type)={hasattr(msg, 'type')}, hasattr(content)={hasattr(msg, 'content')}")
            if hasattr(msg, 'type') and hasattr(msg, 'content'):
                # Map message types to OpenAI roles
                msg_type = getattr(msg, 'type', 'user')
                if msg_type == 'human':
                    role = 'user'
                elif msg_type == 'ai':
                    role = 'assistant'
                elif msg_type == 'tool':
                    # Skip tool messages to avoid malformed structure
                    print(f"🔍 DEBUG: Skipping tool message {i}")
                    continue
                else:
                    # Default to user for unknown types
                    role = 'user'

                prepared_messages.append({"role": role, "content": msg.content})
                print(f"🔍 DEBUG: Message {i}: {role} (was {msg_type}) - {msg.content[:100]}...")
            elif isinstance(msg, dict):
                # Handle dictionary messages
                print(f"🔍 DEBUG: Dict message {i}: keys={list(msg.keys())}")

                # Check if this is a tool result (has success/message structure)
                if 'success' in msg and 'message' in msg:
                    # This is a tool result - include it as a user message so agent can see the result
                    content = f"Previous tool result: {msg.get('message', str(msg))}"
                    prepared_messages.append({"role": "user", "content": content})
                    print(f"🔍 DEBUG: Message {i}: user (tool result) - {content[:100]}...")
                # Check if this is an OpenAI tool call message (has tool_call_id, role, name)
                elif 'tool_call_id' in msg and 'role' in msg and 'name' in msg:
                    # This is an OpenAI tool call result - include the content as a tool result
                    content = msg.get('content', str(msg))
                    if content and content.strip():
                        tool_result_content = f"Tool '{msg.get('name', 'unknown')}' result: {content}"
                        prepared_messages.append({"role": "user", "content": tool_result_content})
                        print(f"🔍 DEBUG: Message {i}: user (OpenAI tool result) - {tool_result_content[:100]}...")
                    else:
                        print(f"🔍 DEBUG: Skipping empty OpenAI tool message {i}")
                else:
                    # Regular dictionary message
                    role = msg.get('role', 'user')
                    # Normalize 'human' role to 'user' for OpenAI compatibility
                    if role == 'human':
                        role = 'user'
                    content = msg.get('content', str(msg))
                    # Skip tool messages to avoid malformed structure
                    if role != 'tool':
                        prepared_messages.append({"role": role, "content": content})
                        print(f"🔍 DEBUG: Message {i}: {role} - {content[:100]}...")
                    else:
                        print(f"🔍 DEBUG: Skipping tool message {i}")
            else:
                # Fallback for other message types - treat as user message
                prepared_messages.append({"role": "user", "content": str(msg)})
                print(f"🔍 DEBUG: Message {i}: user (fallback) - {str(msg)[:100]}...")

        print(f"🔍 DEBUG: Final prepared messages count: {len(prepared_messages)}")
        print(f"🔍 DEBUG: System prompt preview: {full_system_prompt[:200]}...")
        # Show actual user messages
        user_messages = [msg for msg in prepared_messages if msg.get('role') == 'user']
        if user_messages:
            print(f"🔍 DEBUG: Found {len(user_messages)} user messages")
            print(f"🔍 DEBUG: Last user message content: {user_messages[-1]['content'][:200]}...")
        else:
            print(f"🔍 DEBUG: No user messages found in prepared_messages")

        return prepared_messages

    async def _execute_with_monitoring(
        self,
        prepared_messages: List[Dict],
        tools: List[Dict],
        agent_name: str
    ):
        """Execute OpenAI call with performance monitoring."""

        execution_start = time.perf_counter()

        # Check if client is available
        if self.client is None:
            raise Exception("OpenAI client not available - using fallback mode")

        try:
            # 🚀 PHASE 1 OPTIMIZATION: Reduced timeout and optimized parameters for faster responses
            # TODO: If performance degrades, revert timeout to 30.0 and temperature to 0.1
            response = self.client.chat.completions.create(
                model=self.model,
                messages=prepared_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,  # Balanced: creative enough for variations, deterministic enough for tools
                timeout=15.0,     # 🚀 OPTIMIZATION: Balanced timeout - sufficient for formatting, faster failure detection
                max_tokens=2000   # 🚀 OPTIMIZATION: Increased to 2000 to handle multiple contract listings without truncation
            )

            execution_time = time.perf_counter() - execution_start

            # Log slow executions for optimization
            if execution_time > 2.0:
                print(f"⚠️ Slow OpenAI execution for {agent_name}: {execution_time:.2f}s")

            return response

        except Exception as e:
            execution_time = time.perf_counter() - execution_start
            print(f"❌ OpenAI execution failed for {agent_name} after {execution_time:.2f}s: {e}")
            raise

    async def _update_performance_metrics(
        self,
        state: AgentState,
        agent_name: str,
        processing_time: float,
        start_time: float
    ):
        """Update performance metrics with detailed tracking."""

        if 'agent_response_times' not in state:
            state['agent_response_times'] = {}

        state['agent_response_times'][agent_name] = processing_time

        # Track performance trends
        if 'performance_history' not in state:
            state['performance_history'] = []

        state['performance_history'].append({
            'agent': agent_name,
            'processing_time': processing_time,
            'timestamp': start_time,
            'status': 'success'
        })

        # Keep only recent history (last 10 executions)
        if len(state['performance_history']) > 10:
            state['performance_history'] = state['performance_history'][-10:]

    async def _update_memory_async(
        self,
        state: AgentState,
        response_message,
        agent_name: str,
        processing_time: float
    ):
        """Update conversation memory asynchronously to avoid blocking."""

        try:
            await self.memory_manager.update_conversation_history(
                state['context']['session_id'],
                state['context']['user_id'],
                {
                    "role": "assistant",
                    "content": response_message.content,
                    "agent": agent_name,
                    "processing_time": processing_time,
                    "timestamp": time.time()
                }
            )
        except Exception as e:
            print(f"Error updating memory for {agent_name}: {e}")

    def _generate_cache_key(self, state: AgentState, agent_name: str) -> str:
        """Generate cache key for response caching."""

        # Create key based on user message and agent
        last_message = ""
        if state.get('messages'):
            last_msg = state['messages'][-1]
            if hasattr(last_msg, 'content'):
                last_message = last_msg.content[:100]  # First 100 chars

        # Include user context for personalization
        user_id = state.get('context', {}).get('user_id', 'unknown')
        session_id = state.get('context', {}).get('session_id', 'unknown')

        # Include timestamp for test environments to avoid cache conflicts
        # This ensures each test run gets a unique cache key
        import hashlib
        import time
        timestamp_component = ""
        if user_id.startswith('test-') or session_id.startswith('test-'):
            # For test environments, include microsecond timestamp to ensure uniqueness
            timestamp_component = f":{int(time.time() * 1000000)}"

        cache_input = f"{agent_name}:{user_id}:{last_message}{timestamp_component}"
        cache_key = f"agent_response:{hashlib.md5(cache_input.encode()).hexdigest()}"

        return cache_key

    def _is_cache_valid(self, cached_response: Dict, state: AgentState) -> bool:
        """Check if cached response is still valid for current context."""

        # For now, simple validation - can be enhanced with more sophisticated logic
        return isinstance(cached_response, dict) and 'messages' in cached_response

    def _determine_cache_ttl(self, response_content: str) -> int:
        """Determine cache TTL based on response content type."""

        if not response_content:
            return 60  # 1 minute for empty responses

        # Longer TTL for informational responses
        if any(word in response_content.lower() for word in ['created', 'found', 'retrieved']):
            return 300  # 5 minutes

        # Shorter TTL for dynamic content
        if any(word in response_content.lower() for word in ['updated', 'deleted', 'modified']):
            return 60   # 1 minute

        return 180  # 3 minutes default

    async def _track_error(
        self,
        state: AgentState,
        agent_name: str,
        error_message: str,
        processing_time: float
    ):
        """Track errors for monitoring and optimization."""

        if 'error_history' not in state:
            state['error_history'] = []

        state['error_history'].append({
            'agent': agent_name,
            'error': error_message,
            'processing_time': processing_time,
            'timestamp': time.time()
        })

        # Keep only recent errors
        if len(state['error_history']) > 5:
            state['error_history'] = state['error_history'][-5:]

    async def basic_invoke(self, state: AgentState, system_prompt: str, tools: List[Dict]) -> Dict:
        """Fallback basic invocation without memory integration"""
        messages = state['messages']

        # Check if we have an OpenAI client
        if self.client is None:
            print("⚠️ No OpenAI client available, using fallback tool selection")
            return await self._fallback_tool_execution(state, system_prompt, tools)

        prepared_messages = [
            {"role": "system", "content": system_prompt}
        ]

        for msg in messages:
            if hasattr(msg, 'type') and hasattr(msg, 'content'):
                msg_type = getattr(msg, 'type', 'user')
                if msg_type == 'human':
                    role = 'user'
                elif msg_type == 'ai':
                    role = 'assistant'
                elif msg_type == 'tool':
                    # Skip tool messages to avoid malformed structure
                    continue
                else:
                    # Default to user for unknown types
                    role = 'user'
                prepared_messages.append({"role": role, "content": msg.content})
            else:
                prepared_messages.append({"role": "user", "content": str(msg)})

        try:
            # 🚀 PHASE 1 OPTIMIZATION: Reduced timeout and optimized parameters for faster responses
            # TODO: If performance degrades, revert timeout to 30.0 and temperature to 0.1
            response = self.client.chat.completions.create(
                model=self.model,
                messages=prepared_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,  # Balanced: creative enough for variations, deterministic enough for tools
                timeout=15.0,     # 🚀 OPTIMIZATION: Balanced timeout - sufficient for formatting, faster failure detection
                max_tokens=2000   # 🚀 OPTIMIZATION: Increased to 2000 to handle multiple contract listings without truncation
            )

            response_message = response.choices[0].message

            return {"messages": [response_message]}
        except Exception as e:
            print(f"⚠️ OpenAI API call failed: {e}, using fallback tool selection")
            return await self._fallback_tool_execution(state, system_prompt, tools)

    async def _extract_and_save_context(
        self,
        state: AgentState,
        prepared_messages: List[Dict[str, str]],
        response_message
    ):
        """Extract context from user messages and agent response, then save to state['data']."""
        try:
            print(f"🔍 DEBUG: Starting context extraction...")

            # Defensive check: ensure state is not None
            if state is None:
                print(f"🔍 DEBUG: State is None, skipping context extraction")
                return

            print(f"🔍 DEBUG: Prepared messages count: {len(prepared_messages) if prepared_messages else 0}")

            # Extract context from user messages
            user_context = {}
            has_new_user_message = False

            if prepared_messages:
                for i, msg in enumerate(prepared_messages):
                    if msg.get('role') == 'user':
                        # Skip tool results that might be formatted as user messages
                        content = msg['content']
                        if content.startswith("Tool '") and "result:" in content:
                            print(f"🔍 DEBUG: Skipping tool result message: {content[:100]}...")
                            continue

                        print(f"🔍 DEBUG: Processing user message {i}: {content[:100]}...")
                        # Defensive: ensure state has data dict
                        existing_data = state.get('data', {}) if isinstance(state, dict) else {}
                        user_msg_context = context_extractor.extract_context_from_user_message(content, existing_data)
                        print(f"🔍 DEBUG: Extracted from user message: {user_msg_context}")
                        user_context.update(user_msg_context)
                        has_new_user_message = True

            # Only extract context from agent response if there was a new user message and response_message exists
            agent_context = {}
            if has_new_user_message and response_message and hasattr(response_message, 'content') and response_message.content:
                print(f"🔍 DEBUG: Processing agent response: {response_message.content[:100]}...")
                agent_context = context_extractor.extract_context_from_agent_response(response_message.content)
                print(f"🔍 DEBUG: Extracted from agent response: {agent_context}")
            elif not has_new_user_message:
                print(f"🔍 DEBUG: No new user message, skipping context extraction to preserve existing context")
                existing_data = state.get('data', {}) if isinstance(state, dict) else {}
                print(f"🔍 DEBUG: Preserving existing context: {existing_data}")
                return

            # Combine all context
            all_context = {**user_context, **agent_context}
            print(f"🔍 DEBUG: Combined context: {all_context}")

            # Update state with context
            if all_context:
                context_extractor.update_state_with_context(state, all_context)
                print(f"🔍 DEBUG: Context extraction completed: {list(all_context.keys())}")
            else:
                print(f"🔍 DEBUG: No context extracted from messages")

        except Exception as e:
            print(f"🔍 DEBUG: Error in context extraction: {e}")

    async def _should_short_circuit(self, state: AgentState, agent_name: str) -> bool:
        """Check if we should bypass LLM and call tool directly."""
        data = state.get('data', {})

        # Check if we have the required context for direct tool execution
        has_user_operation = 'user_operation' in data
        has_client = 'current_client' in data
        has_contract_id = 'current_contract_id' in data
        has_file_info = 'context' in state and state['context'].get('file_info')
        user_operation = data.get('user_operation')

        print(f"🔍 DEBUG: Short-circuit check - user_operation: {has_user_operation} ({user_operation}), client: {has_client}, contract_id: {has_contract_id}, file_info: {has_file_info}")
        print(f"🔍 DEBUG: Full state data: {data}")

        # Short-circuit for file uploads when file_info exists AND no contract_id is specified yet
        # This prevents short-circuiting during contract selection responses
        if (has_user_operation and has_client and has_file_info and not has_contract_id and
            user_operation == 'upload_contract_document'):
            print(f"🔍 DEBUG: Short-circuiting for initial file upload - calling upload_contract_document directly")
            return True

        # Only short-circuit for simple cases: contract ID responses after a clear operation request
        # This allows the LLM to handle complex field extraction and natural language variations
        if (has_user_operation and has_client and has_contract_id and
            user_operation in ['update_contract', 'delete_contract', 'upload_contract_document']):

            # Check if this is a simple contract ID response (just a number)
            messages = state.get('messages', [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    last_content = last_message.content.strip()
                    # Only short-circuit if the last message is just a contract ID (simple number)
                    if last_content.isdigit():
                        print(f"🔍 DEBUG: Short-circuiting LLM call - direct tool execution")
                        return True

        print(f"🔍 DEBUG: Short-circuit conditions NOT met - letting LLM handle the request")
        return False

    async def _execute_direct_tool_call(self, state: AgentState, agent_name: str) -> Dict:
        """Execute tool directly without LLM when we have all context."""
        data = state.get('data', {})
        user_operation = data.get('user_operation')
        client_name = data.get('current_client')
        contract_id = data.get('current_contract_id')
        original_request = data.get('original_user_request', '')

        print(f"🔍 DEBUG: Direct tool execution - {user_operation} for {client_name} with contract {contract_id}")

        # Map user operation to tool function
        tool_mapping = {
            'update_contract': 'update_contract_tool',
            'delete_contract': 'delete_contract_tool',
            'create_contract': 'create_contract_tool',
            'upload_contract_document': 'upload_contract_document_tool'
        }

        tool_name = tool_mapping.get(user_operation)
        if not tool_name:
            print(f"🔍 DEBUG: No tool mapping for {user_operation}")
            return {"messages": [{"role": "assistant", "content": f"I don't know how to handle {user_operation} operation."}]}

        # Import the tool function
        from ..tools.contract_tools import (
            update_contract_tool, delete_contract_tool,
            smart_create_contract_tool, upload_contract_document_tool
        )

        tool_functions = {
            'update_contract_tool': update_contract_tool,
            'delete_contract_tool': delete_contract_tool,
            'create_contract_tool': smart_create_contract_tool,
            'upload_contract_document_tool': upload_contract_document_tool
        }

        tool_function = tool_functions.get(tool_name)
        if not tool_function:
            print(f"🔍 DEBUG: Tool function not found: {tool_name}")
            return {"messages": [{"role": "assistant", "content": f"Tool function {tool_name} not found."}]}

        try:
            # Prepare tool arguments based on operation
            if user_operation == 'update_contract':
                from ..tools.contract_tools import UpdateContractParams
                params = UpdateContractParams(
                    client_name=client_name,
                    contract_id=int(contract_id) if contract_id else None
                    # Note: Let LLM handle other field extraction for better flexibility
                )
            elif user_operation == 'delete_contract':
                from ..tools.contract_tools import DeleteContractParams
                params = DeleteContractParams(
                    client_name=client_name,
                    contract_id=int(contract_id) if contract_id else None
                )
            elif user_operation == 'upload_contract_document':
                # Handle upload operation with preserved context
                from ..tools.contract_tools import UploadContractDocumentParams
                params = UploadContractDocumentParams(
                    client_name=client_name,
                    contract_id=int(contract_id) if contract_id else None,
                    file_data="<base64_encoded_data>",  # Placeholder - will be replaced by wrapper
                    filename="[USE_ACTUAL_FILE_DATA_FROM_CONTEXT]",   # Placeholder - will be replaced by wrapper
                    file_size=0,  # Placeholder - will be replaced by wrapper
                    mime_type="[USE_ACTUAL_FILE_DATA_FROM_CONTEXT]"   # Placeholder - will be replaced by wrapper
                )
            else:
                # For other operations, create basic params
                params = {"client_name": client_name, "user_response": contract_id}

            # Call the tool directly
            print(f"🔍 DEBUG: Calling {tool_name} with params: {params}")
            result = await tool_function(params, state.get('context', {}))

            # Format the result as a message
            if hasattr(result, 'message'):
                response_content = result.message
                result_data = getattr(result, 'data', None)
            elif isinstance(result, dict) and 'message' in result:
                response_content = result['message']
                result_data = result.get('data', None)
            else:
                response_content = str(result)
                result_data = None

            print(f"🔍 DIRECT TOOL: Tool result content: {response_content[:100]}...")
            if result_data:
                print(f"🔍 DIRECT TOOL: Tool result data keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'Not a dict'}")

            # Include structured data if available - use same format as regular agent execution
            message = {"type": "ai", "content": response_content, "role": "assistant"}
            if result_data:
                message["data"] = result_data
                print(f"🔍 DIRECT TOOL: Added data to message, total message keys: {list(message.keys())}")
            else:
                print(f"🔍 DIRECT TOOL: No data to add, message keys: {list(message.keys())}")

            print(f"🔍 DIRECT TOOL: Final message type: {type(message)}")
            print(f"🔍 DIRECT TOOL: Final message content type: {type(message.get('content'))}")
            print(f"🔍 DIRECT TOOL: Final message content length: {len(str(message.get('content', '')))}")

            return {"messages": [message]}

        except Exception as e:
            print(f"🔍 DEBUG: Error in direct tool execution: {e}")
            return {"messages": [{"role": "assistant", "content": f"Error executing {user_operation}: {str(e)}"}]}

    async def _lookup_contract_and_save_client_name(self, state: AgentState):
        """Look up contract details by ID and save client name in context."""
        try:
            contract_id = state.get('data', {}).get('current_contract_id')
            if not contract_id:
                return

            print(f"🔍 DEBUG: Looking up contract {contract_id} to get client name")

            # Import here to avoid circular imports
            from src.database.core.database import get_ai_db
            from src.database.core.models import Contract, Client
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            async with get_ai_db() as session:
                # Get contract with client information
                # Convert contract_id to integer to match database column type
                contract_id_int = int(contract_id)
                result = await session.execute(
                    select(Contract)
                    .options(selectinload(Contract.client))
                    .filter(Contract.contract_id == contract_id_int)
                )
                contract = result.scalar_one_or_none()

                if contract and contract.client:
                    client_name = contract.client.client_name
                    print(f"🔍 DEBUG: Found client name for contract {contract_id}: {client_name}")

                    # Save client name in state
                    if 'data' not in state:
                        state['data'] = {}
                    state['data']['current_client'] = client_name
                    print(f"🔍 DEBUG: Saved client name in context: {client_name}")
                else:
                    print(f"🔍 DEBUG: Contract {contract_id} not found or has no client")

        except Exception as e:
            print(f"🔍 DEBUG: Error looking up contract {contract_id}: {e}")


# --- Agent Node Definitions ---
enhanced_executor = EnhancedAgentNodeExecutor()

# Instantiate agents for enhanced execution
contract_agent_instance = ContractAgent()
employee_agent_instance = EmployeeAgent()
client_agent_instance = ClientAgent()
deliverable_agent_instance = DeliverableAgent()
time_agent_instance = TimeTrackerAgent()
user_agent_instance = UserAgent()


# Sync wrapper functions for compatibility
def contract_agent_node_sync(state: AgentState) -> Dict:
    """Sync wrapper for contract agent node."""
    print("--- Running Enhanced Contract Agent Node (Sync) ---")
    result = asyncio.run(enhanced_executor.invoke(state, contract_agent_instance, "contract_agent"))
    print(f"🔍 DEBUG: Sync contract agent result type: {type(result)}")
    print(f"🔍 DEBUG: Sync contract agent result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    if isinstance(result, dict) and 'messages' in result and result['messages']:
        print(f"🔍 DEBUG: Sync contract agent message content: {result['messages'][0].get('content', 'No content')}")
    return result

def employee_agent_node_sync(state: AgentState) -> Dict:
    """Sync wrapper for employee agent node."""
    print("--- Running Enhanced Employee Agent Node (Sync) ---")

    result = asyncio.run(enhanced_executor.invoke(state, employee_agent_instance, "employee_agent"))

    return result

def client_agent_node_sync(state: AgentState) -> Dict:
    """Sync wrapper for client agent node."""
    print("--- Running Enhanced Client Agent Node (Sync) ---")
    return asyncio.run(enhanced_executor.invoke(state, client_agent_instance, "client_agent"))

def deliverable_agent_node_sync(state: AgentState) -> Dict:
    """Sync wrapper for deliverable agent node."""
    print("--- Running Enhanced Deliverable Agent Node (Sync) ---")
    return asyncio.run(enhanced_executor.invoke(state, deliverable_agent_instance, "deliverable_agent"))

def time_agent_node_sync(state: AgentState) -> Dict:
    """Sync wrapper for time agent node."""
    print("--- Running Enhanced Time Agent Node (Sync) ---")
    return asyncio.run(enhanced_executor.invoke(state, time_agent_instance, "time_agent"))

def user_agent_node_sync(state: AgentState) -> Dict:
    """Sync wrapper for user agent node."""
    print("--- Running Enhanced User Agent Node (Sync) ---")
    return asyncio.run(enhanced_executor.invoke(state, user_agent_instance, "user_agent"))

# Async versions
async def contract_agent_node_async(state: AgentState) -> Dict:
    """
    Enhanced contract agent node with memory integration.
    """
    print("--- Running Enhanced Contract Agent Node ---")
    return await enhanced_executor.invoke(state, contract_agent_instance, "contract_agent")

async def employee_agent_node_async(state: AgentState) -> Dict:
    """
    Enhanced employee agent node with memory integration.
    """
    print("--- Running Enhanced Employee Agent Node ---")

    result = await enhanced_executor.invoke(state, employee_agent_instance, "employee_agent")

    return result

async def client_agent_node_async(state: AgentState) -> Dict:
    """
    Enhanced client agent node with memory integration.
    """
    print("--- Running Enhanced Client Agent Node ---")
    print(f"🔍 DEBUG: Client Agent - state keys: {list(state.keys()) if isinstance(state, dict) else 'Not a dict'}")
    print(f"🔍 DEBUG: Client Agent - data: {state.get('data', {})}")
    print(f"🔍 DEBUG: Client Agent - context: {state.get('context', {})}")

    try:
        result = await enhanced_executor.invoke(state, client_agent_instance, "client_agent")
        print(f"🔍 DEBUG: Client Agent - execution completed successfully")
        return result
    except Exception as e:
        print(f"❌ Client Agent - execution failed: {e}")
        import traceback
        print(f"❌ Client Agent - full traceback: {traceback.format_exc()}")
        raise

async def deliverable_agent_node_async(state: AgentState) -> Dict:
    """
    Enhanced deliverable agent node with memory integration.
    """
    print("--- Running Enhanced Deliverable Agent Node ---")
    return await enhanced_executor.invoke(state, deliverable_agent_instance, "deliverable_agent")

async def time_agent_node_async(state: AgentState) -> Dict:
    """
    Enhanced time agent node with memory integration.
    """
    print("--- Running Enhanced Time Agent Node ---")
    return await enhanced_executor.invoke(state, time_agent_instance, "time_agent")

async def user_agent_node_async(state: AgentState) -> Dict:
    """
    Enhanced user agent node with memory integration.
    """
    print("--- Running Enhanced User Agent Node ---")
    return await enhanced_executor.invoke(state, user_agent_instance, "user_agent")

# Hybrid functions that work with both sync and async calls
def contract_agent_node(state: AgentState) -> Dict:
    """Hybrid contract agent node that works with both sync and async calls."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return contract_agent_node_sync(state)
        else:
            return asyncio.run(contract_agent_node_async(state))
    except RuntimeError:
        return contract_agent_node_sync(state)

def employee_agent_node(state: AgentState) -> Dict:
    """Hybrid employee agent node that works with both sync and async calls."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return employee_agent_node_sync(state)
        else:
            return asyncio.run(employee_agent_node_async(state))
    except RuntimeError:
        return employee_agent_node_sync(state)

def client_agent_node(state: AgentState) -> Dict:
    """Hybrid client agent node that works with both sync and async calls."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return client_agent_node_sync(state)
        else:
            return asyncio.run(client_agent_node_async(state))
    except RuntimeError:
        return client_agent_node_sync(state)

def deliverable_agent_node(state: AgentState) -> Dict:
    """Hybrid deliverable agent node that works with both sync and async calls."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return deliverable_agent_node_sync(state)
        else:
            return asyncio.run(deliverable_agent_node_async(state))
    except RuntimeError:
        return deliverable_agent_node_sync(state)

def time_agent_node(state: AgentState) -> Dict:
    """Hybrid time agent node that works with both sync and async calls."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return time_agent_node_sync(state)
        else:
            return asyncio.run(time_agent_node_async(state))
    except RuntimeError:
        return time_agent_node_sync(state)

def user_agent_node(state: AgentState) -> Dict:
    """Hybrid user agent node that works with both sync and async calls."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return user_agent_node_sync(state)
        else:
            return asyncio.run(user_agent_node_async(state))
    except RuntimeError:
        return user_agent_node_sync(state)

"""
High-Performance Parallel Agent Executor

Optimized for minimum latency with:
- Concurrent agent execution
- Efficient resource pooling
- Minimal context switching overhead
- Fast state synchronization
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum

from ..graph.state import AgentState
from ..memory.context_manager import ContextManager


class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"


@dataclass
class ExecutionResult:
    agent_name: str
    success: bool
    result: Any
    execution_time: float
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    mode: ExecutionMode
    agents: List[str]
    dependencies: Dict[str, List[str]]  # agent -> list of dependencies
    timeout: float = 30.0


class ParallelAgentExecutor:
    """
    High-performance executor for running multiple agents with minimal latency.
    
    Features:
    - Async-first design for maximum concurrency
    - Dependency-aware execution ordering
    - Resource pooling to minimize overhead
    - Fast context sharing between agents
    """
    
    def __init__(self, max_concurrent_agents: int = 5):
        self.max_concurrent_agents = max_concurrent_agents
        self.context_manager = ContextManager()
        self._execution_semaphore = asyncio.Semaphore(max_concurrent_agents)
        self._agent_cache = {}  # Cache agent instances for reuse
        
    async def execute_parallel(
        self, 
        execution_plan: ExecutionPlan, 
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> List[ExecutionResult]:
        """
        Execute agents according to the execution plan with optimal performance.
        
        Args:
            execution_plan: Plan defining how agents should be executed
            state: Current agent state
            agent_registry: Available agents
            
        Returns:
            List of execution results with timing information
        """
        start_time = time.perf_counter()
        
        if execution_plan.mode == ExecutionMode.SEQUENTIAL:
            results = await self._execute_sequential(execution_plan, state, agent_registry)
        elif execution_plan.mode == ExecutionMode.PARALLEL:
            results = await self._execute_parallel_concurrent(execution_plan, state, agent_registry)
        else:  # PIPELINE
            results = await self._execute_pipeline(execution_plan, state, agent_registry)
            
        total_time = time.perf_counter() - start_time
        
        # Update performance metrics
        await self._update_performance_metrics(results, total_time)
        
        return results
    
    async def _execute_parallel_concurrent(
        self, 
        execution_plan: ExecutionPlan, 
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> List[ExecutionResult]:
        """Execute agents concurrently with dependency management."""
        
        # Build execution graph
        execution_graph = self._build_execution_graph(execution_plan)
        results = {}
        
        # Execute in waves based on dependencies
        for wave in execution_graph:
            wave_tasks = []
            
            for agent_name in wave:
                if agent_name in agent_registry:
                    task = self._execute_single_agent(
                        agent_name, 
                        agent_registry[agent_name], 
                        state.copy() if hasattr(state, 'copy') else state,
                        results
                    )
                    wave_tasks.append(task)
            
            # Execute wave concurrently
            if wave_tasks:
                wave_results = await asyncio.gather(*wave_tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(wave_results):
                    agent_name = wave[i]
                    if isinstance(result, Exception):
                        results[agent_name] = ExecutionResult(
                            agent_name=agent_name,
                            success=False,
                            result=None,
                            execution_time=0.0,
                            error=str(result)
                        )
                    else:
                        results[agent_name] = result
        
        return list(results.values())
    
    async def _execute_single_agent(
        self, 
        agent_name: str, 
        agent: Any, 
        state: AgentState,
        previous_results: Dict[str, ExecutionResult]
    ) -> ExecutionResult:
        """Execute a single agent with performance optimization."""
        
        async with self._execution_semaphore:
            start_time = time.perf_counter()
            
            try:
                # Optimize context building - only include relevant context
                optimized_context = await self._build_optimized_context(
                    agent_name, state, previous_results
                )
                
                # Update state with optimized context
                state["context"].update(optimized_context)
                
                # Execute agent
                if hasattr(agent, 'ainvoke'):
                    result = await agent.ainvoke(state)
                else:
                    # Fallback to sync execution in thread pool
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, agent.invoke, state
                    )
                
                execution_time = time.perf_counter() - start_time
                
                return ExecutionResult(
                    agent_name=agent_name,
                    success=True,
                    result=result,
                    execution_time=execution_time
                )
                
            except Exception as e:
                execution_time = time.perf_counter() - start_time
                return ExecutionResult(
                    agent_name=agent_name,
                    success=False,
                    result=None,
                    execution_time=execution_time,
                    error=str(e)
                )
    
    async def _build_optimized_context(
        self, 
        agent_name: str, 
        state: AgentState,
        previous_results: Dict[str, ExecutionResult]
    ) -> Dict[str, Any]:
        """
        Build minimal, optimized context for the agent to reduce latency.
        Only include relevant information to minimize processing overhead.
        """
        
        # Start with minimal context
        optimized_context = {
            "agent_name": agent_name,
            "execution_mode": "parallel",
            "timestamp": time.time()
        }
        
        # Add relevant previous results (only successful ones)
        relevant_results = {}
        for name, result in previous_results.items():
            if result.success and self._is_result_relevant(agent_name, name, result):
                relevant_results[name] = {
                    "result": result.result,
                    "execution_time": result.execution_time
                }
        
        if relevant_results:
            optimized_context["previous_results"] = relevant_results
        
        # Add user context (cached for performance)
        user_context = await self._get_cached_user_context(state["context"]["user_id"])
        if user_context:
            optimized_context["user"] = user_context
        
        return optimized_context
    
    def _build_execution_graph(self, execution_plan: ExecutionPlan) -> List[List[str]]:
        """Build execution waves based on dependencies for optimal parallelization."""
        
        if not execution_plan.dependencies:
            # No dependencies - all agents can run in parallel
            return [execution_plan.agents]
        
        # Topological sort to determine execution order
        waves = []
        remaining_agents = set(execution_plan.agents)
        completed_agents = set()
        
        while remaining_agents:
            # Find agents with no pending dependencies
            ready_agents = []
            for agent in remaining_agents:
                dependencies = execution_plan.dependencies.get(agent, [])
                if all(dep in completed_agents for dep in dependencies):
                    ready_agents.append(agent)
            
            if not ready_agents:
                # Circular dependency or missing agent - break the cycle
                ready_agents = [next(iter(remaining_agents))]
            
            waves.append(ready_agents)
            remaining_agents -= set(ready_agents)
            completed_agents.update(ready_agents)
        
        return waves
    
    async def _execute_sequential(
        self, 
        execution_plan: ExecutionPlan, 
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> List[ExecutionResult]:
        """Execute agents sequentially for cases where order matters."""
        
        results = []
        results_dict = {}
        
        for agent_name in execution_plan.agents:
            if agent_name in agent_registry:
                result = await self._execute_single_agent(
                    agent_name, 
                    agent_registry[agent_name], 
                    state, 
                    results_dict
                )
                results.append(result)
                results_dict[agent_name] = result
                
                # Update state with result for next agent
                if result.success:
                    state["data"][f"{agent_name}_result"] = result.result
        
        return results
    
    async def _execute_pipeline(
        self, 
        execution_plan: ExecutionPlan, 
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> List[ExecutionResult]:
        """Execute agents in pipeline mode where output of one feeds into next."""
        
        results = []
        current_state = state
        
        for agent_name in execution_plan.agents:
            if agent_name in agent_registry:
                result = await self._execute_single_agent(
                    agent_name, 
                    agent_registry[agent_name], 
                    current_state, 
                    {}
                )
                results.append(result)
                
                # Pipeline: output becomes input for next agent
                if result.success and result.result:
                    if isinstance(result.result, dict) and "messages" in result.result:
                        current_state = result.result
                    else:
                        current_state["data"]["pipeline_input"] = result.result
        
        return results
    
    def _is_result_relevant(self, agent_name: str, result_agent: str, result: ExecutionResult) -> bool:
        """Determine if a previous result is relevant for the current agent."""
        
        # Simple relevance rules - can be enhanced with ML-based relevance scoring
        relevance_map = {
            "client_agent": ["contract_agent", "deliverable_agent"],
            "contract_agent": ["client_agent", "deliverable_agent", "time_agent"],
            "employee_agent": ["time_agent", "deliverable_agent"],
            "deliverable_agent": ["client_agent", "contract_agent", "employee_agent"],
            "time_agent": ["employee_agent", "contract_agent", "deliverable_agent"]
        }
        
        return result_agent in relevance_map.get(agent_name, [])
    
    async def _get_cached_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user context to minimize database queries."""
        
        # This would integrate with the caching system
        # For now, return minimal context
        return {
            "user_id": user_id,
            "cached": True
        }
    
    async def _update_performance_metrics(self, results: List[ExecutionResult], total_time: float):
        """Update performance metrics for monitoring and optimization."""
        
        # Calculate metrics
        successful_executions = sum(1 for r in results if r.success)
        failed_executions = len(results) - successful_executions
        avg_execution_time = sum(r.execution_time for r in results) / len(results) if results else 0
        
        # Store metrics (would integrate with metrics collection system)
        metrics = {
            "total_agents": len(results),
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "total_time": total_time,
            "avg_execution_time": avg_execution_time,
            "timestamp": time.time()
        }
        
        # Log for monitoring (in production, this would go to metrics system)
        print(f"Parallel execution metrics: {metrics}")


def create_execution_plan(
    agents: List[str], 
    mode: ExecutionMode = ExecutionMode.PARALLEL,
    dependencies: Optional[Dict[str, List[str]]] = None,
    timeout: float = 30.0
) -> ExecutionPlan:
    """Helper function to create execution plans."""
    
    return ExecutionPlan(
        mode=mode,
        agents=agents,
        dependencies=dependencies or {},
        timeout=timeout
    )

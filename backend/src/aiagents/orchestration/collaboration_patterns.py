"""
Agent Collaboration Patterns

High-performance collaboration patterns for multi-agent workflows:
- Sequential execution with handoffs
- Parallel execution with synchronization
- Hierarchical coordination
- Pipeline processing
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from ..graph.state import AgentState
from .parallel_executor import ParallelAgentExecutor, ExecutionPlan, ExecutionMode


class CollaborationPattern(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"


@dataclass
class CollaborationStep:
    agents: List[str]
    pattern: CollaborationPattern
    condition: Optional[Callable[[AgentState], bool]] = None
    timeout: float = 30.0
    retry_count: int = 0


class CollaborationOrchestrator:
    """
    High-performance orchestrator for agent collaboration patterns.
    
    Features:
    - Multiple collaboration patterns
    - Conditional execution flows
    - Performance optimization
    - Error handling and recovery
    """
    
    def __init__(self):
        self.parallel_executor = ParallelAgentExecutor()
        self._execution_stats = {
            "total_collaborations": 0,
            "successful_collaborations": 0,
            "failed_collaborations": 0,
            "avg_execution_time": 0.0
        }
    
    async def execute_collaboration(
        self,
        steps: List[CollaborationStep],
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a multi-step collaboration workflow.
        
        Performance target: Minimize total execution time through optimal patterns
        """
        start_time = time.perf_counter()
        
        try:
            self._execution_stats["total_collaborations"] += 1
            
            results = []
            current_state = state.copy() if hasattr(state, 'copy') else state
            
            for step_index, step in enumerate(steps):
                print(f"🔄 Executing collaboration step {step_index + 1}/{len(steps)}: {step.pattern.value}")
                
                # Check condition if specified
                if step.condition and not step.condition(current_state):
                    print(f"⏭️ Skipping step {step_index + 1} due to condition")
                    continue
                
                # Execute step based on pattern
                step_result = await self._execute_step(
                    step, current_state, agent_registry
                )
                
                results.append({
                    "step_index": step_index,
                    "pattern": step.pattern.value,
                    "agents": step.agents,
                    "result": step_result
                })
                
                # Update state for next step
                current_state = self._merge_step_result(current_state, step_result)
            
            execution_time = time.perf_counter() - start_time
            self._execution_stats["successful_collaborations"] += 1
            self._update_avg_execution_time(execution_time)
            
            return {
                "success": True,
                "results": results,
                "final_state": current_state,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            self._execution_stats["failed_collaborations"] += 1
            
            print(f"❌ Collaboration failed after {execution_time:.2f}s: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def _execute_step(
        self,
        step: CollaborationStep,
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single collaboration step."""
        
        if step.pattern == CollaborationPattern.SEQUENTIAL:
            return await self._execute_sequential(step, state, agent_registry)
        
        elif step.pattern == CollaborationPattern.PARALLEL:
            return await self._execute_parallel(step, state, agent_registry)
        
        elif step.pattern == CollaborationPattern.HIERARCHICAL:
            return await self._execute_hierarchical(step, state, agent_registry)
        
        elif step.pattern == CollaborationPattern.PIPELINE:
            return await self._execute_pipeline(step, state, agent_registry)
        
        elif step.pattern == CollaborationPattern.CONDITIONAL:
            return await self._execute_conditional(step, state, agent_registry)
        
        else:
            raise ValueError(f"Unknown collaboration pattern: {step.pattern}")
    
    async def _execute_sequential(
        self,
        step: CollaborationStep,
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute agents sequentially with state passing."""
        
        execution_plan = ExecutionPlan(
            mode=ExecutionMode.SEQUENTIAL,
            agents=step.agents,
            dependencies={},
            timeout=step.timeout
        )
        
        results = await self.parallel_executor.execute_parallel(
            execution_plan, state, agent_registry
        )
        
        return {
            "pattern": "sequential",
            "results": results,
            "agents_executed": len([r for r in results if r.success])
        }
    
    async def _execute_parallel(
        self,
        step: CollaborationStep,
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute agents in parallel for maximum performance."""
        
        execution_plan = ExecutionPlan(
            mode=ExecutionMode.PARALLEL,
            agents=step.agents,
            dependencies={},
            timeout=step.timeout
        )
        
        results = await self.parallel_executor.execute_parallel(
            execution_plan, state, agent_registry
        )
        
        return {
            "pattern": "parallel",
            "results": results,
            "agents_executed": len([r for r in results if r.success])
        }
    
    async def _execute_hierarchical(
        self,
        step: CollaborationStep,
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute agents in hierarchical pattern (supervisor -> workers)."""
        
        if not step.agents:
            return {"pattern": "hierarchical", "results": [], "agents_executed": 0}
        
        # First agent is supervisor, rest are workers
        supervisor = step.agents[0]
        workers = step.agents[1:] if len(step.agents) > 1 else []
        
        results = []
        
        # Execute supervisor first
        if supervisor in agent_registry:
            supervisor_result = await self._execute_single_agent(
                supervisor, state, agent_registry[supervisor]
            )
            results.append(supervisor_result)
            
            # Update state with supervisor result
            if supervisor_result.success:
                state = self._merge_agent_result(state, supervisor_result)
        
        # Execute workers in parallel if any
        if workers:
            worker_plan = ExecutionPlan(
                mode=ExecutionMode.PARALLEL,
                agents=workers,
                dependencies={},
                timeout=step.timeout
            )
            
            worker_results = await self.parallel_executor.execute_parallel(
                worker_plan, state, agent_registry
            )
            
            results.extend(worker_results)
        
        return {
            "pattern": "hierarchical",
            "results": results,
            "agents_executed": len([r for r in results if r.success])
        }
    
    async def _execute_pipeline(
        self,
        step: CollaborationStep,
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute agents in pipeline pattern (output -> input)."""
        
        execution_plan = ExecutionPlan(
            mode=ExecutionMode.PIPELINE,
            agents=step.agents,
            dependencies={},
            timeout=step.timeout
        )
        
        results = await self.parallel_executor.execute_parallel(
            execution_plan, state, agent_registry
        )
        
        return {
            "pattern": "pipeline",
            "results": results,
            "agents_executed": len([r for r in results if r.success])
        }
    
    async def _execute_conditional(
        self,
        step: CollaborationStep,
        state: AgentState,
        agent_registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute agents based on dynamic conditions."""
        
        # For conditional execution, evaluate which agents should run
        agents_to_execute = []
        
        for agent in step.agents:
            # Simple condition: execute if agent hasn't been used recently
            if self._should_execute_agent(agent, state):
                agents_to_execute.append(agent)
        
        if not agents_to_execute:
            return {
                "pattern": "conditional",
                "results": [],
                "agents_executed": 0,
                "message": "No agents met execution conditions"
            }
        
        # Execute selected agents in parallel
        execution_plan = ExecutionPlan(
            mode=ExecutionMode.PARALLEL,
            agents=agents_to_execute,
            dependencies={},
            timeout=step.timeout
        )
        
        results = await self.parallel_executor.execute_parallel(
            execution_plan, state, agent_registry
        )
        
        return {
            "pattern": "conditional",
            "results": results,
            "agents_executed": len([r for r in results if r.success]),
            "agents_selected": agents_to_execute
        }
    
    async def _execute_single_agent(
        self,
        agent_name: str,
        state: AgentState,
        agent_instance: Any
    ):
        """Execute a single agent (helper method)."""
        
        start_time = time.perf_counter()
        
        try:
            # This would use the enhanced executor from nodes.py
            from ..graph.nodes import enhanced_executor
            
            result = await enhanced_executor.invoke(state, agent_instance, agent_name)
            
            execution_time = time.perf_counter() - start_time
            
            return type('Result', (), {
                'agent_name': agent_name,
                'success': True,
                'result': result,
                'execution_time': execution_time,
                'error': None
            })()
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            
            return type('Result', (), {
                'agent_name': agent_name,
                'success': False,
                'result': None,
                'execution_time': execution_time,
                'error': str(e)
            })()
    
    def _merge_step_result(self, state: AgentState, step_result: Dict[str, Any]) -> AgentState:
        """Merge step results into the state."""
        
        # Update collaboration history
        if 'collaboration_history' not in state:
            state['collaboration_history'] = []
        
        state['collaboration_history'].append({
            'pattern': step_result.get('pattern'),
            'agents_executed': step_result.get('agents_executed', 0),
            'timestamp': time.time()
        })
        
        # Keep only recent history
        if len(state['collaboration_history']) > 5:
            state['collaboration_history'] = state['collaboration_history'][-5:]
        
        return state
    
    def _merge_agent_result(self, state: AgentState, agent_result) -> AgentState:
        """Merge individual agent result into state."""
        
        if agent_result.success and agent_result.result:
            # Update messages if available
            if isinstance(agent_result.result, dict) and 'messages' in agent_result.result:
                if 'messages' not in state:
                    state['messages'] = []
                state['messages'].extend(agent_result.result['messages'])
        
        return state
    
    def _should_execute_agent(self, agent_name: str, state: AgentState) -> bool:
        """Determine if an agent should be executed based on conditions."""
        
        # Simple condition: check if agent was used recently
        agent_response_times = state.get('agent_response_times', {})
        
        # Execute if agent hasn't been used or was used more than 30 seconds ago
        if agent_name not in agent_response_times:
            return True
        
        # For now, always execute (can be enhanced with more sophisticated logic)
        return True
    
    def _update_avg_execution_time(self, execution_time: float):
        """Update average execution time with exponential moving average."""
        
        alpha = 0.1  # Smoothing factor
        if self._execution_stats["avg_execution_time"] == 0:
            self._execution_stats["avg_execution_time"] = execution_time
        else:
            self._execution_stats["avg_execution_time"] = (
                alpha * execution_time + 
                (1 - alpha) * self._execution_stats["avg_execution_time"]
            )
    
    def get_collaboration_stats(self) -> Dict[str, Any]:
        """Get collaboration statistics for monitoring."""
        return self._execution_stats.copy()


# Convenience functions for common collaboration patterns
async def execute_sequential_collaboration(
    agents: List[str],
    state: AgentState,
    agent_registry: Dict[str, Any],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Execute agents sequentially."""
    
    orchestrator = CollaborationOrchestrator()
    steps = [CollaborationStep(
        agents=agents,
        pattern=CollaborationPattern.SEQUENTIAL,
        timeout=timeout
    )]
    
    return await orchestrator.execute_collaboration(steps, state, agent_registry)


async def execute_parallel_collaboration(
    agents: List[str],
    state: AgentState,
    agent_registry: Dict[str, Any],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Execute agents in parallel."""
    
    orchestrator = CollaborationOrchestrator()
    steps = [CollaborationStep(
        agents=agents,
        pattern=CollaborationPattern.PARALLEL,
        timeout=timeout
    )]
    
    return await orchestrator.execute_collaboration(steps, state, agent_registry)


async def execute_supervisor_worker_collaboration(
    supervisor: str,
    workers: List[str],
    state: AgentState,
    agent_registry: Dict[str, Any],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Execute supervisor-worker pattern."""
    
    orchestrator = CollaborationOrchestrator()
    steps = [CollaborationStep(
        agents=[supervisor] + workers,
        pattern=CollaborationPattern.HIERARCHICAL,
        timeout=timeout
    )]
    
    return await orchestrator.execute_collaboration(steps, state, agent_registry)

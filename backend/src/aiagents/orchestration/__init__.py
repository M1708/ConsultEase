"""
Phase 2 Advanced Agent Orchestration

This module provides high-performance, low-latency orchestration capabilities:
- Parallel agent execution with minimal overhead
- Efficient state synchronization
- Optimized context sharing
- Performance-first design patterns
"""

from .parallel_executor import ParallelAgentExecutor
from .agent_pool import AgentPool
from .collaboration_patterns import CollaborationOrchestrator
from .state_synchronizer import StateSynchronizer

__all__ = [
    "ParallelAgentExecutor",
    "AgentPool", 
    "CollaborationOrchestrator",
    "StateSynchronizer"
]

"""
Agent Pool Management

High-performance agent instance management with:
- Agent instance pooling and reuse
- Resource optimization
- Load balancing across agent instances
- Minimal initialization overhead
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
from enum import Enum

from ..graph.state import AgentState


class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    INITIALIZING = "initializing"


@dataclass
class AgentInstance:
    agent_id: str
    agent_type: str
    instance: Any
    status: AgentStatus
    created_at: float
    last_used: float
    usage_count: int
    error_count: int


class AgentPool:
    """
    High-performance agent pool for managing agent instances.
    
    Features:
    - Instance reuse to minimize initialization overhead
    - Load balancing across multiple instances
    - Automatic cleanup of unused instances
    - Performance monitoring and optimization
    """
    
    def __init__(self, max_instances_per_type: int = 3):
        self.max_instances_per_type = max_instances_per_type
        self._pools: Dict[str, List[AgentInstance]] = {}
        self._agent_classes: Dict[str, Type] = {}
        self._pool_lock = asyncio.Lock()
        
        # Performance tracking
        self._pool_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "instances_created": 0,
            "instances_destroyed": 0
        }
    
    def register_agent_class(self, agent_type: str, agent_class: Type):
        """Register an agent class for pooling."""
        self._agent_classes[agent_type] = agent_class
        if agent_type not in self._pools:
            self._pools[agent_type] = []
    
    async def get_agent(self, agent_type: str) -> Optional[AgentInstance]:
        """
        Get an available agent instance from the pool.
        
        Performance target: <5ms for pool hits, <50ms for new instances
        """
        start_time = time.perf_counter()
        
        async with self._pool_lock:
            self._pool_stats["total_requests"] += 1
            
            # Try to get an idle instance from pool
            if agent_type in self._pools:
                for instance in self._pools[agent_type]:
                    if instance.status == AgentStatus.IDLE:
                        # Mark as busy and update usage
                        instance.status = AgentStatus.BUSY
                        instance.last_used = time.time()
                        instance.usage_count += 1
                        
                        self._pool_stats["cache_hits"] += 1
                        
                        get_time = time.perf_counter() - start_time
                        if get_time > 0.005:  # Log if over 5ms
                            print(f"Slow pool get: {get_time:.3f}s for {agent_type}")
                        
                        return instance
            
            # No idle instance available, create new one if under limit
            if self._can_create_instance(agent_type):
                instance = await self._create_instance(agent_type)
                if instance:
                    self._pool_stats["cache_misses"] += 1
                    self._pool_stats["instances_created"] += 1
                    
                    get_time = time.perf_counter() - start_time
                    print(f"Created new {agent_type} instance in {get_time:.3f}s")
                    
                    return instance
            
            # Pool is full and no idle instances
            print(f"Agent pool exhausted for {agent_type}")
            return None
    
    async def return_agent(self, instance: AgentInstance):
        """Return an agent instance to the pool."""
        
        async with self._pool_lock:
            if instance.error_count > 5:
                # Remove problematic instances
                await self._remove_instance(instance)
                self._pool_stats["instances_destroyed"] += 1
            else:
                # Mark as idle for reuse
                instance.status = AgentStatus.IDLE
    
    async def cleanup_unused_instances(self, max_idle_time: float = 300.0):
        """Clean up instances that haven't been used recently."""
        
        current_time = time.time()
        
        async with self._pool_lock:
            for agent_type, instances in self._pools.items():
                instances_to_remove = []
                
                for instance in instances:
                    if (instance.status == AgentStatus.IDLE and 
                        current_time - instance.last_used > max_idle_time):
                        instances_to_remove.append(instance)
                
                # Remove old instances
                for instance in instances_to_remove:
                    await self._remove_instance(instance)
                    self._pool_stats["instances_destroyed"] += 1
    
    def _can_create_instance(self, agent_type: str) -> bool:
        """Check if we can create a new instance for the agent type."""
        
        if agent_type not in self._pools:
            return True
        
        return len(self._pools[agent_type]) < self.max_instances_per_type
    
    async def _create_instance(self, agent_type: str) -> Optional[AgentInstance]:
        """Create a new agent instance."""
        
        if agent_type not in self._agent_classes:
            print(f"Unknown agent type: {agent_type}")
            return None
        
        try:
            # Create agent instance
            agent_class = self._agent_classes[agent_type]
            agent_instance = agent_class()
            
            # Create pool instance
            instance = AgentInstance(
                agent_id=f"{agent_type}_{int(time.time() * 1000)}",
                agent_type=agent_type,
                instance=agent_instance,
                status=AgentStatus.BUSY,  # Start as busy
                created_at=time.time(),
                last_used=time.time(),
                usage_count=1,
                error_count=0
            )
            
            # Add to pool
            if agent_type not in self._pools:
                self._pools[agent_type] = []
            
            self._pools[agent_type].append(instance)
            
            return instance
            
        except Exception as e:
            print(f"Error creating {agent_type} instance: {e}")
            return None
    
    async def _remove_instance(self, instance: AgentInstance):
        """Remove an instance from the pool."""
        
        if instance.agent_type in self._pools:
            if instance in self._pools[instance.agent_type]:
                self._pools[instance.agent_type].remove(instance)
        
        # Cleanup instance if needed
        if hasattr(instance.instance, 'cleanup'):
            try:
                await instance.instance.cleanup()
            except Exception as e:
                print(f"Error cleaning up {instance.agent_type} instance: {e}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics for monitoring."""
        
        pool_info = {}
        for agent_type, instances in self._pools.items():
            pool_info[agent_type] = {
                "total_instances": len(instances),
                "idle_instances": sum(1 for i in instances if i.status == AgentStatus.IDLE),
                "busy_instances": sum(1 for i in instances if i.status == AgentStatus.BUSY),
                "error_instances": sum(1 for i in instances if i.status == AgentStatus.ERROR),
                "avg_usage": sum(i.usage_count for i in instances) / len(instances) if instances else 0
            }
        
        return {
            "global_stats": self._pool_stats,
            "pool_info": pool_info,
            "total_pools": len(self._pools)
        }
    
    async def warm_pool(self, agent_type: str, count: int = 1):
        """Pre-warm the pool with agent instances."""
        
        print(f"Warming pool for {agent_type} with {count} instances...")
        
        for _ in range(count):
            if self._can_create_instance(agent_type):
                instance = await self._create_instance(agent_type)
                if instance:
                    # Mark as idle immediately for warming
                    instance.status = AgentStatus.IDLE
                    instance.usage_count = 0  # Reset usage count for warmed instances


# Global agent pool instance
agent_pool = AgentPool()


# Convenience functions
async def get_pooled_agent(agent_type: str) -> Optional[AgentInstance]:
    """Get an agent instance from the global pool."""
    return await agent_pool.get_agent(agent_type)


async def return_pooled_agent(instance: AgentInstance):
    """Return an agent instance to the global pool."""
    await agent_pool.return_agent(instance)


def register_agent_for_pooling(agent_type: str, agent_class: Type):
    """Register an agent class for pooling."""
    agent_pool.register_agent_class(agent_type, agent_class)

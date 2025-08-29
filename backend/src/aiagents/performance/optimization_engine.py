"""
Phase 2 Optimization Engine

Automatic performance optimization and resource management:
- Dynamic resource allocation
- Performance bottleneck detection
- Automatic scaling decisions
- Cache optimization strategies
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class OptimizationStrategy(Enum):
    """Available optimization strategies"""
    LATENCY_FOCUSED = "latency_focused"
    THROUGHPUT_FOCUSED = "throughput_focused"
    BALANCED = "balanced"
    RESOURCE_CONSERVATIVE = "resource_conservative"

@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization decisions"""
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    active_agents: int = 0
    queue_depth: int = 0
    timestamp: float = field(default_factory=time.time)

@dataclass
class OptimizationRecommendation:
    """Optimization recommendation with confidence score"""
    action: str
    parameters: Dict[str, Any]
    confidence: float
    expected_improvement: float
    risk_level: str
    description: str

class OptimizationEngine:
    """
    Automatic optimization engine for Phase 2 performance
    
    Features:
    - Real-time performance analysis
    - Dynamic optimization recommendations
    - Automatic parameter tuning
    - Resource allocation optimization
    """
    
    def __init__(
        self,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        optimization_interval: float = 30.0,
        min_data_points: int = 10
    ):
        self.strategy = strategy
        self.optimization_interval = optimization_interval
        self.min_data_points = min_data_points
        
        # Performance history
        self.metrics_history: deque = deque(maxlen=1000)
        self.optimization_history: List[OptimizationRecommendation] = []
        
        # Current optimization parameters
        self.current_params = {
            "cache_ttl": 300,
            "max_parallel_agents": 10,
            "agent_pool_size": 5,
            "batch_size": 1,
            "timeout": 30.0,
            "retry_attempts": 3
        }
        
        # Performance thresholds
        self.thresholds = {
            "max_response_time": 200.0,  # ms
            "max_error_rate": 0.05,      # 5%
            "min_cache_hit_rate": 0.7,   # 70%
            "max_memory_usage": 0.8,     # 80%
            "max_cpu_usage": 0.8         # 80%
        }
        
        self._running = False
        self._optimization_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the optimization engine"""
        if self._running:
            return
            
        self._running = True
        self._optimization_task = asyncio.create_task(self._optimization_loop())
        logger.info(f"Optimization engine started with strategy: {self.strategy.value}")
    
    async def stop(self):
        """Stop the optimization engine"""
        self._running = False
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        logger.info("Optimization engine stopped")
    
    def record_metrics(self, metrics: PerformanceMetrics):
        """Record performance metrics for analysis"""
        self.metrics_history.append(metrics)
        
        # Trigger immediate optimization if critical thresholds exceeded
        if self._should_optimize_immediately(metrics):
            asyncio.create_task(self._perform_optimization())
    
    def _should_optimize_immediately(self, metrics: PerformanceMetrics) -> bool:
        """Check if immediate optimization is needed"""
        return (
            metrics.avg_response_time > self.thresholds["max_response_time"] * 2 or
            metrics.error_rate > self.thresholds["max_error_rate"] * 2 or
            metrics.memory_usage > 0.9 or
            metrics.cpu_usage > 0.9
        )
    
    async def _optimization_loop(self):
        """Main optimization loop"""
        while self._running:
            try:
                await asyncio.sleep(self.optimization_interval)
                if len(self.metrics_history) >= self.min_data_points:
                    await self._perform_optimization()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
    
    async def _perform_optimization(self):
        """Perform optimization analysis and apply recommendations"""
        try:
            # Analyze current performance
            analysis = self._analyze_performance()
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analysis)
            
            # Apply high-confidence, low-risk recommendations
            for rec in recommendations:
                if rec.confidence > 0.8 and rec.risk_level == "low":
                    await self._apply_recommendation(rec)
                    self.optimization_history.append(rec)
                    logger.info(f"Applied optimization: {rec.description}")
            
        except Exception as e:
            logger.error(f"Error during optimization: {e}")
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze recent performance metrics"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = list(self.metrics_history)[-50:]  # Last 50 data points
        
        analysis = {
            "avg_response_time": sum(m.avg_response_time for m in recent_metrics) / len(recent_metrics),
            "avg_throughput": sum(m.throughput for m in recent_metrics) / len(recent_metrics),
            "avg_error_rate": sum(m.error_rate for m in recent_metrics) / len(recent_metrics),
            "avg_cache_hit_rate": sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics),
            "avg_memory_usage": sum(m.memory_usage for m in recent_metrics) / len(recent_metrics),
            "avg_cpu_usage": sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics),
            "trend_response_time": self._calculate_trend([m.avg_response_time for m in recent_metrics]),
            "trend_throughput": self._calculate_trend([m.throughput for m in recent_metrics]),
            "trend_error_rate": self._calculate_trend([m.error_rate for m in recent_metrics])
        }
        
        return analysis
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a series of values"""
        if len(values) < 2:
            return "stable"
        
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        change_pct = (second_avg - first_avg) / first_avg if first_avg > 0 else 0
        
        if change_pct > 0.1:
            return "increasing"
        elif change_pct < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on analysis"""
        recommendations = []
        
        # Response time optimization
        if analysis.get("avg_response_time", 0) > self.thresholds["max_response_time"]:
            if analysis.get("avg_cache_hit_rate", 1) < self.thresholds["min_cache_hit_rate"]:
                recommendations.append(OptimizationRecommendation(
                    action="increase_cache_ttl",
                    parameters={"new_ttl": self.current_params["cache_ttl"] * 1.5},
                    confidence=0.85,
                    expected_improvement=0.2,
                    risk_level="low",
                    description="Increase cache TTL to improve hit rate and reduce response time"
                ))
            
            if self.current_params["max_parallel_agents"] < 20:
                recommendations.append(OptimizationRecommendation(
                    action="increase_parallelism",
                    parameters={"new_max": min(self.current_params["max_parallel_agents"] + 2, 20)},
                    confidence=0.75,
                    expected_improvement=0.15,
                    risk_level="medium",
                    description="Increase parallel agent limit to handle more concurrent requests"
                ))
        
        # Throughput optimization
        if analysis.get("trend_throughput") == "decreasing":
            recommendations.append(OptimizationRecommendation(
                action="increase_batch_size",
                parameters={"new_batch_size": min(self.current_params["batch_size"] + 1, 5)},
                confidence=0.7,
                expected_improvement=0.1,
                risk_level="low",
                description="Increase batch size to improve throughput"
            ))
        
        # Error rate optimization
        if analysis.get("avg_error_rate", 0) > self.thresholds["max_error_rate"]:
            recommendations.append(OptimizationRecommendation(
                action="increase_timeout",
                parameters={"new_timeout": min(self.current_params["timeout"] + 5, 60)},
                confidence=0.8,
                expected_improvement=0.3,
                risk_level="low",
                description="Increase timeout to reduce timeout-related errors"
            ))
            
            recommendations.append(OptimizationRecommendation(
                action="increase_retries",
                parameters={"new_retries": min(self.current_params["retry_attempts"] + 1, 5)},
                confidence=0.75,
                expected_improvement=0.25,
                risk_level="low",
                description="Increase retry attempts to handle transient failures"
            ))
        
        # Resource optimization
        if analysis.get("avg_memory_usage", 0) > self.thresholds["max_memory_usage"]:
            recommendations.append(OptimizationRecommendation(
                action="reduce_cache_ttl",
                parameters={"new_ttl": max(self.current_params["cache_ttl"] * 0.8, 60)},
                confidence=0.9,
                expected_improvement=0.2,
                risk_level="low",
                description="Reduce cache TTL to free up memory"
            ))
        
        return recommendations
    
    async def _apply_recommendation(self, recommendation: OptimizationRecommendation):
        """Apply an optimization recommendation"""
        action = recommendation.action
        params = recommendation.parameters
        
        if action == "increase_cache_ttl":
            self.current_params["cache_ttl"] = params["new_ttl"]
        elif action == "reduce_cache_ttl":
            self.current_params["cache_ttl"] = params["new_ttl"]
        elif action == "increase_parallelism":
            self.current_params["max_parallel_agents"] = params["new_max"]
        elif action == "increase_batch_size":
            self.current_params["batch_size"] = params["new_batch_size"]
        elif action == "increase_timeout":
            self.current_params["timeout"] = params["new_timeout"]
        elif action == "increase_retries":
            self.current_params["retry_attempts"] = params["new_retries"]
    
    def get_current_parameters(self) -> Dict[str, Any]:
        """Get current optimization parameters"""
        return self.current_params.copy()
    
    def get_optimization_history(self) -> List[OptimizationRecommendation]:
        """Get history of applied optimizations"""
        return self.optimization_history.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics_history:
            return {}
        
        recent = list(self.metrics_history)[-10:]
        
        return {
            "current_response_time": recent[-1].avg_response_time if recent else 0,
            "current_throughput": recent[-1].throughput if recent else 0,
            "current_error_rate": recent[-1].error_rate if recent else 0,
            "current_cache_hit_rate": recent[-1].cache_hit_rate if recent else 0,
            "optimizations_applied": len(self.optimization_history),
            "last_optimization": self.optimization_history[-1].timestamp if self.optimization_history else None
        }

# Global optimization engine instance
_optimization_engine: Optional[OptimizationEngine] = None

def get_optimization_engine() -> OptimizationEngine:
    """Get global optimization engine instance"""
    global _optimization_engine
    if _optimization_engine is None:
        _optimization_engine = OptimizationEngine()
    return _optimization_engine

async def start_optimization_engine():
    """Start the global optimization engine"""
    engine = get_optimization_engine()
    await engine.start()

async def stop_optimization_engine():
    """Stop the global optimization engine"""
    engine = get_optimization_engine()
    await engine.stop()

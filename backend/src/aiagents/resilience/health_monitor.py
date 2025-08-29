"""
Phase 2 Health Monitor Implementation

Comprehensive health monitoring for system resilience:
- Real-time health status tracking
- Configurable health checks
- Automatic alerting and notifications
- Health metrics aggregation
"""

import asyncio
import time
from typing import Any, Callable, Optional, Dict, List, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str
    timestamp: float
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HealthAlert:
    """Health alert information"""
    component: str
    level: AlertLevel
    message: str
    timestamp: float
    resolved: bool = False
    resolved_timestamp: Optional[float] = None

class HealthCheck(ABC):
    """Abstract base class for health checks"""
    
    def __init__(self, name: str, timeout: float = 10.0):
        self.name = name
        self.timeout = timeout
    
    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """Perform the health check"""
        pass

class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity"""
    
    def __init__(self, name: str = "database", db_session_factory: Optional[Callable] = None):
        super().__init__(name)
        self.db_session_factory = db_session_factory
    
    async def check(self) -> HealthCheckResult:
        """Check database connectivity"""
        start_time = time.time()
        
        try:
            if self.db_session_factory:
                # Test database connection
                session = self.db_session_factory()
                # Simple query to test connectivity
                session.execute("SELECT 1")
                session.close()
                
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    timestamp=start_time,
                    duration=time.time() - start_time
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNKNOWN,
                    message="No database session factory configured",
                    timestamp=start_time,
                    duration=time.time() - start_time
                )
                
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                timestamp=start_time,
                duration=time.time() - start_time
            )

class RedisHealthCheck(HealthCheck):
    """Health check for Redis connectivity"""
    
    def __init__(self, name: str = "redis", redis_client: Optional[Any] = None):
        super().__init__(name)
        self.redis_client = redis_client
    
    async def check(self) -> HealthCheckResult:
        """Check Redis connectivity"""
        start_time = time.time()
        
        try:
            if self.redis_client:
                # Test Redis connection
                await self.redis_client.ping()
                
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Redis connection successful",
                    timestamp=start_time,
                    duration=time.time() - start_time
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNKNOWN,
                    message="No Redis client configured",
                    timestamp=start_time,
                    duration=time.time() - start_time
                )
                
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                timestamp=start_time,
                duration=time.time() - start_time
            )

class OpenAIHealthCheck(HealthCheck):
    """Health check for OpenAI API connectivity"""
    
    def __init__(self, name: str = "openai", openai_client: Optional[Any] = None):
        super().__init__(name)
        self.openai_client = openai_client
    
    async def check(self) -> HealthCheckResult:
        """Check OpenAI API connectivity"""
        start_time = time.time()
        
        try:
            if self.openai_client:
                # Test OpenAI API with a simple request
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="OpenAI API connection successful",
                    timestamp=start_time,
                    duration=time.time() - start_time
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNKNOWN,
                    message="No OpenAI client configured",
                    timestamp=start_time,
                    duration=time.time() - start_time
                )
                
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"OpenAI API connection failed: {str(e)}",
                timestamp=start_time,
                duration=time.time() - start_time
            )

class MemoryHealthCheck(HealthCheck):
    """Health check for memory usage"""
    
    def __init__(self, name: str = "memory", max_memory_percent: float = 80.0):
        super().__init__(name)
        self.max_memory_percent = max_memory_percent
    
    async def check(self) -> HealthCheckResult:
        """Check memory usage"""
        start_time = time.time()
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent > self.max_memory_percent:
                status = HealthStatus.UNHEALTHY
                message = f"High memory usage: {memory_percent:.1f}%"
            elif memory_percent > self.max_memory_percent * 0.8:
                status = HealthStatus.DEGRADED
                message = f"Elevated memory usage: {memory_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory_percent:.1f}%"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                timestamp=start_time,
                duration=time.time() - start_time,
                metadata={"memory_percent": memory_percent}
            )
            
        except ImportError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="psutil not available for memory monitoring",
                timestamp=start_time,
                duration=time.time() - start_time
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {str(e)}",
                timestamp=start_time,
                duration=time.time() - start_time
            )

class HealthMonitor:
    """
    Comprehensive health monitoring system
    
    Features:
    - Multiple health check types
    - Configurable check intervals
    - Automatic alerting
    - Health metrics aggregation
    """
    
    def __init__(
        self,
        check_interval: float = 30.0,
        alert_threshold: int = 3,
        recovery_threshold: int = 2
    ):
        self.check_interval = check_interval
        self.alert_threshold = alert_threshold
        self.recovery_threshold = recovery_threshold
        
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_history: Dict[str, List[HealthCheckResult]] = {}
        self.alerts: List[HealthAlert] = []
        self.consecutive_failures: Dict[str, int] = {}
        self.consecutive_successes: Dict[str, int] = {}
        
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    def add_health_check(self, health_check: HealthCheck):
        """Add a health check to the monitor"""
        self.health_checks[health_check.name] = health_check
        self.health_history[health_check.name] = []
        self.consecutive_failures[health_check.name] = 0
        self.consecutive_successes[health_check.name] = 0
        logger.info(f"Added health check: {health_check.name}")
    
    def remove_health_check(self, name: str):
        """Remove a health check from the monitor"""
        if name in self.health_checks:
            del self.health_checks[name]
            del self.health_history[name]
            del self.consecutive_failures[name]
            del self.consecutive_successes[name]
            logger.info(f"Removed health check: {name}")
    
    async def start(self):
        """Start the health monitor"""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")
    
    async def stop(self):
        """Stop the health monitor"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _perform_health_checks(self):
        """Perform all health checks"""
        tasks = []
        for name, health_check in self.health_checks.items():
            task = asyncio.create_task(self._run_health_check(health_check))
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, HealthCheckResult):
                    await self._process_health_result(result)
                elif isinstance(result, Exception):
                    logger.error(f"Health check failed with exception: {result}")
    
    async def _run_health_check(self, health_check: HealthCheck) -> HealthCheckResult:
        """Run a single health check with timeout"""
        try:
            return await asyncio.wait_for(
                health_check.check(),
                timeout=health_check.timeout
            )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                name=health_check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {health_check.timeout}s",
                timestamp=time.time(),
                duration=health_check.timeout
            )
        except Exception as e:
            return HealthCheckResult(
                name=health_check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=time.time(),
                duration=0.0
            )
    
    async def _process_health_result(self, result: HealthCheckResult):
        """Process a health check result"""
        # Store result in history
        self.health_history[result.name].append(result)
        
        # Keep only recent history (last 100 results)
        if len(self.health_history[result.name]) > 100:
            self.health_history[result.name] = self.health_history[result.name][-100:]
        
        # Update consecutive counters
        if result.status == HealthStatus.HEALTHY:
            self.consecutive_failures[result.name] = 0
            self.consecutive_successes[result.name] += 1
        else:
            self.consecutive_failures[result.name] += 1
            self.consecutive_successes[result.name] = 0
        
        # Check for alerts
        await self._check_alerts(result)
    
    async def _check_alerts(self, result: HealthCheckResult):
        """Check if alerts should be triggered or resolved"""
        name = result.name
        
        # Check for new alerts
        if (result.status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED] and
            self.consecutive_failures[name] >= self.alert_threshold):
            
            # Check if alert already exists
            existing_alert = None
            for alert in self.alerts:
                if alert.component == name and not alert.resolved:
                    existing_alert = alert
                    break
            
            if not existing_alert:
                level = AlertLevel.CRITICAL if result.status == HealthStatus.UNHEALTHY else AlertLevel.WARNING
                alert = HealthAlert(
                    component=name,
                    level=level,
                    message=f"Health check '{name}' failing: {result.message}",
                    timestamp=time.time()
                )
                self.alerts.append(alert)
                logger.warning(f"Health alert triggered: {alert.message}")
        
        # Check for alert resolution
        if (result.status == HealthStatus.HEALTHY and
            self.consecutive_successes[name] >= self.recovery_threshold):
            
            # Resolve any open alerts for this component
            for alert in self.alerts:
                if alert.component == name and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_timestamp = time.time()
                    logger.info(f"Health alert resolved: {alert.message}")
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        if not self.health_checks:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": "No health checks configured",
                "components": {}
            }
        
        component_statuses = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, history in self.health_history.items():
            if not history:
                component_statuses[name] = HealthStatus.UNKNOWN.value
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.UNKNOWN
            else:
                latest = history[-1]
                component_statuses[name] = latest.status.value
                
                # Determine overall status (worst case)
                if latest.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif latest.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
                elif latest.status == HealthStatus.UNKNOWN and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.UNKNOWN
        
        return {
            "status": overall_status.value,
            "message": f"System health: {overall_status.value}",
            "components": component_statuses,
            "timestamp": time.time()
        }
    
    def get_component_health(self, name: str) -> Optional[Dict[str, Any]]:
        """Get health status for a specific component"""
        if name not in self.health_history or not self.health_history[name]:
            return None
        
        latest = self.health_history[name][-1]
        recent_results = self.health_history[name][-10:]  # Last 10 results
        
        success_rate = sum(1 for r in recent_results if r.status == HealthStatus.HEALTHY) / len(recent_results)
        avg_duration = sum(r.duration for r in recent_results) / len(recent_results)
        
        return {
            "name": name,
            "status": latest.status.value,
            "message": latest.message,
            "timestamp": latest.timestamp,
            "duration": latest.duration,
            "success_rate": success_rate,
            "average_duration": avg_duration,
            "consecutive_failures": self.consecutive_failures[name],
            "consecutive_successes": self.consecutive_successes[name],
            "metadata": latest.metadata
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        return [
            {
                "component": alert.component,
                "level": alert.level.value,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "duration": time.time() - alert.timestamp
            }
            for alert in active_alerts
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get health monitoring metrics"""
        total_checks = sum(len(history) for history in self.health_history.values())
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts if not a.resolved])
        
        return {
            "total_health_checks": len(self.health_checks),
            "total_check_executions": total_checks,
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "check_interval": self.check_interval,
            "uptime": time.time() - (self.health_history[list(self.health_history.keys())[0]][0].timestamp if self.health_history and list(self.health_history.values())[0] else time.time())
        }

# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None

def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor

async def start_health_monitor():
    """Start the global health monitor"""
    monitor = get_health_monitor()
    await monitor.start()

async def stop_health_monitor():
    """Stop the global health monitor"""
    monitor = get_health_monitor()
    await monitor.stop()

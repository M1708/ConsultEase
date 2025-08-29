"""
Phase 2 Circuit Breaker Implementation

Enterprise-grade circuit breaker pattern for fault tolerance:
- Automatic failure detection
- Configurable thresholds and timeouts
- Half-open state for recovery testing
- Metrics collection and monitoring
"""

import asyncio
import time
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import deque

logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Number of failures to open circuit
    recovery_timeout: float = 60.0      # Seconds before trying half-open
    success_threshold: int = 3          # Successes needed to close from half-open
    timeout: float = 30.0               # Request timeout in seconds
    expected_exception: type = Exception # Exception type to count as failure
    
@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opened_count: int = 0
    circuit_closed_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_successes: deque = field(default_factory=lambda: deque(maxlen=100))

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance
    
    Features:
    - Automatic failure detection and recovery
    - Configurable thresholds and timeouts
    - Comprehensive metrics collection
    - Support for async and sync operations
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self.last_failure_time = 0.0
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self._lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenException: When circuit is open
            TimeoutError: When function times out
            Exception: Original function exceptions
        """
        async with self._lock:
            # Check if circuit should be opened
            if self.state == CircuitBreakerState.CLOSED:
                if self.consecutive_failures >= self.config.failure_threshold:
                    await self._open_circuit()
            
            # Check if circuit should transition to half-open
            elif self.state == CircuitBreakerState.OPEN:
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    await self._half_open_circuit()
        
        # Handle different states
        if self.state == CircuitBreakerState.OPEN:
            self.metrics.total_requests += 1
            raise CircuitBreakerOpenException(
                f"Circuit breaker '{self.name}' is open. "
                f"Last failure: {time.time() - self.last_failure_time:.1f}s ago"
            )
        
        # Execute the function
        self.metrics.total_requests += 1
        start_time = time.time()
        
        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
            else:
                result = func(*args, **kwargs)
            
            # Record success
            await self._record_success()
            return result
            
        except asyncio.TimeoutError:
            await self._record_failure(f"Timeout after {self.config.timeout}s")
            raise TimeoutError(f"Function timed out after {self.config.timeout}s")
            
        except self.config.expected_exception as e:
            await self._record_failure(str(e))
            raise
            
        except Exception as e:
            # Unexpected exceptions don't count as circuit breaker failures
            logger.warning(f"Unexpected exception in circuit breaker '{self.name}': {e}")
            raise
    
    async def _record_success(self):
        """Record a successful execution"""
        async with self._lock:
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = time.time()
            self.metrics.recent_successes.append(time.time())
            self.consecutive_failures = 0
            self.consecutive_successes += 1
            
            # Close circuit if in half-open state with enough successes
            if (self.state == CircuitBreakerState.HALF_OPEN and 
                self.consecutive_successes >= self.config.success_threshold):
                await self._close_circuit()
    
    async def _record_failure(self, error_msg: str):
        """Record a failed execution"""
        async with self._lock:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = time.time()
            self.metrics.recent_failures.append({
                'time': time.time(),
                'error': error_msg
            })
            self.last_failure_time = time.time()
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            
            logger.warning(
                f"Circuit breaker '{self.name}' recorded failure: {error_msg}. "
                f"Consecutive failures: {self.consecutive_failures}"
            )
    
    async def _open_circuit(self):
        """Open the circuit breaker"""
        if self.state != CircuitBreakerState.OPEN:
            self.state = CircuitBreakerState.OPEN
            self.metrics.circuit_opened_count += 1
            logger.warning(
                f"Circuit breaker '{self.name}' opened after "
                f"{self.consecutive_failures} consecutive failures"
            )
    
    async def _half_open_circuit(self):
        """Transition circuit breaker to half-open state"""
        self.state = CircuitBreakerState.HALF_OPEN
        self.consecutive_successes = 0
        logger.info(f"Circuit breaker '{self.name}' transitioned to half-open")
    
    async def _close_circuit(self):
        """Close the circuit breaker"""
        self.state = CircuitBreakerState.CLOSED
        self.metrics.circuit_closed_count += 1
        self.consecutive_failures = 0
        logger.info(
            f"Circuit breaker '{self.name}' closed after "
            f"{self.consecutive_successes} consecutive successes"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return {
            'name': self.name,
            'state': self.state.value,
            'total_requests': self.metrics.total_requests,
            'successful_requests': self.metrics.successful_requests,
            'failed_requests': self.metrics.failed_requests,
            'success_rate': (
                self.metrics.successful_requests / self.metrics.total_requests
                if self.metrics.total_requests > 0 else 0
            ),
            'consecutive_failures': self.consecutive_failures,
            'consecutive_successes': self.consecutive_successes,
            'circuit_opened_count': self.metrics.circuit_opened_count,
            'circuit_closed_count': self.metrics.circuit_closed_count,
            'last_failure_time': self.metrics.last_failure_time,
            'last_success_time': self.metrics.last_success_time,
            'time_since_last_failure': (
                time.time() - self.last_failure_time if self.last_failure_time > 0 else None
            )
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of circuit breaker"""
        metrics = self.get_metrics()
        
        # Determine health based on state and recent performance
        if self.state == CircuitBreakerState.OPEN:
            health = "unhealthy"
            status = "Circuit breaker is open due to failures"
        elif self.state == CircuitBreakerState.HALF_OPEN:
            health = "degraded"
            status = "Circuit breaker is testing recovery"
        else:
            recent_success_rate = metrics['success_rate']
            if recent_success_rate >= 0.95:
                health = "healthy"
                status = "Circuit breaker operating normally"
            elif recent_success_rate >= 0.8:
                health = "degraded"
                status = "Circuit breaker has elevated error rate"
            else:
                health = "unhealthy"
                status = "Circuit breaker has high error rate"
        
        return {
            'health': health,
            'status': status,
            'state': self.state.value,
            'success_rate': metrics['success_rate'],
            'total_requests': metrics['total_requests']
        }
    
    async def reset(self):
        """Reset circuit breaker to closed state"""
        async with self._lock:
            self.state = CircuitBreakerState.CLOSED
            self.consecutive_failures = 0
            self.consecutive_successes = 0
            self.last_failure_time = 0.0
            logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator interface for circuit breaker"""
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await self.call(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return asyncio.run(self.call(func, *args, **kwargs))
            return sync_wrapper

# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get or create a circuit breaker by name"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]

def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all registered circuit breakers"""
    return _circuit_breakers.copy()

def reset_all_circuit_breakers():
    """Reset all circuit breakers"""
    async def _reset_all():
        for cb in _circuit_breakers.values():
            await cb.reset()
    
    asyncio.run(_reset_all())

# Decorator for easy circuit breaker usage
def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator to add circuit breaker protection to a function"""
    cb = get_circuit_breaker(name, config)
    return cb

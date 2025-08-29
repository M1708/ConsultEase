"""
Phase 2 Retry Strategies Implementation

Intelligent retry patterns for resilient operations:
- Exponential backoff with jitter
- Linear backoff strategies
- Configurable retry conditions
- Comprehensive retry metrics
"""

import asyncio
import random
import time
from typing import Any, Callable, Optional, Dict, List, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class RetryResult(Enum):
    """Retry operation results"""
    SUCCESS = "success"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_NON_RETRYABLE = "failed_non_retryable"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"

@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    attempt_number: int
    start_time: float
    end_time: Optional[float] = None
    exception: Optional[Exception] = None
    result: Optional[Any] = None
    delay_before_attempt: float = 0.0

@dataclass
class RetryMetrics:
    """Metrics for retry operations"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_attempts: int = 0
    total_retry_time: float = 0.0
    attempts_by_operation: List[List[RetryAttempt]] = field(default_factory=list)

class RetryStrategy(ABC):
    """Abstract base class for retry strategies"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        non_retryable_exceptions: Optional[List[Type[Exception]]] = None,
        retry_condition: Optional[Callable[[Exception], bool]] = None
    ):
        self.max_attempts = max_attempts
        self.retryable_exceptions = retryable_exceptions or [Exception]
        self.non_retryable_exceptions = non_retryable_exceptions or []
        self.retry_condition = retry_condition
        self.metrics = RetryMetrics()
    
    @abstractmethod
    def calculate_delay(self, attempt: int, last_exception: Optional[Exception] = None) -> float:
        """Calculate delay before next retry attempt"""
        pass
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if operation should be retried"""
        if attempt >= self.max_attempts:
            return False
        
        # Check non-retryable exceptions first
        for exc_type in self.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False
        
        # Check custom retry condition
        if self.retry_condition:
            return self.retry_condition(exception)
        
        # Check retryable exceptions
        for exc_type in self.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        return False
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        operation_start = time.time()
        attempts = []
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            attempt_info = RetryAttempt(
                attempt_number=attempt,
                start_time=time.time()
            )
            
            # Calculate delay for this attempt (0 for first attempt)
            if attempt > 1:
                delay = self.calculate_delay(attempt - 1, last_exception)
                attempt_info.delay_before_attempt = delay
                if delay > 0:
                    await asyncio.sleep(delay)
            
            try:
                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success!
                attempt_info.end_time = time.time()
                attempt_info.result = result
                attempts.append(attempt_info)
                
                # Update metrics
                self._update_metrics_success(attempts, operation_start)
                
                logger.info(
                    f"Operation succeeded on attempt {attempt}/{self.max_attempts} "
                    f"after {time.time() - operation_start:.2f}s"
                )
                
                return result
                
            except Exception as e:
                attempt_info.end_time = time.time()
                attempt_info.exception = e
                attempts.append(attempt_info)
                last_exception = e
                
                logger.warning(
                    f"Attempt {attempt}/{self.max_attempts} failed: {str(e)}"
                )
                
                # Check if we should retry
                if not self.should_retry(e, attempt):
                    logger.error(
                        f"Operation failed permanently after {attempt} attempts: {str(e)}"
                    )
                    self._update_metrics_failure(attempts, operation_start)
                    raise e
        
        # All attempts exhausted
        logger.error(
            f"Operation failed after {self.max_attempts} attempts. "
            f"Last error: {str(last_exception)}"
        )
        self._update_metrics_failure(attempts, operation_start)
        raise last_exception
    
    def _update_metrics_success(self, attempts: List[RetryAttempt], operation_start: float):
        """Update metrics for successful operation"""
        self.metrics.total_operations += 1
        self.metrics.successful_operations += 1
        self.metrics.total_attempts += len(attempts)
        self.metrics.total_retry_time += time.time() - operation_start
        self.metrics.attempts_by_operation.append(attempts)
    
    def _update_metrics_failure(self, attempts: List[RetryAttempt], operation_start: float):
        """Update metrics for failed operation"""
        self.metrics.total_operations += 1
        self.metrics.failed_operations += 1
        self.metrics.total_attempts += len(attempts)
        self.metrics.total_retry_time += time.time() - operation_start
        self.metrics.attempts_by_operation.append(attempts)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retry strategy metrics"""
        return {
            'total_operations': self.metrics.total_operations,
            'successful_operations': self.metrics.successful_operations,
            'failed_operations': self.metrics.failed_operations,
            'success_rate': (
                self.metrics.successful_operations / self.metrics.total_operations
                if self.metrics.total_operations > 0 else 0
            ),
            'total_attempts': self.metrics.total_attempts,
            'average_attempts_per_operation': (
                self.metrics.total_attempts / self.metrics.total_operations
                if self.metrics.total_operations > 0 else 0
            ),
            'total_retry_time': self.metrics.total_retry_time,
            'average_retry_time': (
                self.metrics.total_retry_time / self.metrics.total_operations
                if self.metrics.total_operations > 0 else 0
            )
        }

class ExponentialBackoffRetry(RetryStrategy):
    """
    Exponential backoff retry strategy with jitter
    
    Features:
    - Exponential delay increase
    - Optional jitter to prevent thundering herd
    - Configurable base delay and multiplier
    - Maximum delay cap
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_range: float = 0.1,
        **kwargs
    ):
        super().__init__(max_attempts=max_attempts, **kwargs)
        self.base_delay = base_delay
        self.multiplier = multiplier
        self.max_delay = max_delay
        self.jitter = jitter
        self.jitter_range = jitter_range
    
    def calculate_delay(self, attempt: int, last_exception: Optional[Exception] = None) -> float:
        """Calculate exponential backoff delay with optional jitter"""
        # Calculate base exponential delay
        delay = self.base_delay * (self.multiplier ** (attempt - 1))
        
        # Apply maximum delay cap
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            jitter_offset = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter_offset)
        
        return delay

class LinearBackoffRetry(RetryStrategy):
    """
    Linear backoff retry strategy
    
    Features:
    - Linear delay increase
    - Configurable base delay and increment
    - Maximum delay cap
    - Optional jitter
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        increment: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = False,
        jitter_range: float = 0.1,
        **kwargs
    ):
        super().__init__(max_attempts=max_attempts, **kwargs)
        self.base_delay = base_delay
        self.increment = increment
        self.max_delay = max_delay
        self.jitter = jitter
        self.jitter_range = jitter_range
    
    def calculate_delay(self, attempt: int, last_exception: Optional[Exception] = None) -> float:
        """Calculate linear backoff delay"""
        # Calculate linear delay
        delay = self.base_delay + (self.increment * (attempt - 1))
        
        # Apply maximum delay cap
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            jitter_offset = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter_offset)
        
        return delay

class FixedDelayRetry(RetryStrategy):
    """
    Fixed delay retry strategy
    
    Features:
    - Constant delay between attempts
    - Optional jitter
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        jitter: bool = False,
        jitter_range: float = 0.1,
        **kwargs
    ):
        super().__init__(max_attempts=max_attempts, **kwargs)
        self.delay = delay
        self.jitter = jitter
        self.jitter_range = jitter_range
    
    def calculate_delay(self, attempt: int, last_exception: Optional[Exception] = None) -> float:
        """Calculate fixed delay"""
        delay = self.delay
        
        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            jitter_offset = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter_offset)
        
        return delay

class AdaptiveRetry(RetryStrategy):
    """
    Adaptive retry strategy that adjusts based on exception type
    
    Features:
    - Different delays for different exception types
    - Adaptive behavior based on recent success/failure patterns
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        exception_delays: Optional[Dict[Type[Exception], float]] = None,
        default_delay: float = 1.0,
        adaptive_multiplier: float = 1.5,
        **kwargs
    ):
        super().__init__(max_attempts=max_attempts, **kwargs)
        self.exception_delays = exception_delays or {}
        self.default_delay = default_delay
        self.adaptive_multiplier = adaptive_multiplier
        self.recent_failures = []
    
    def calculate_delay(self, attempt: int, last_exception: Optional[Exception] = None) -> float:
        """Calculate adaptive delay based on exception type and recent patterns"""
        base_delay = self.default_delay
        
        # Use exception-specific delay if available
        if last_exception:
            for exc_type, delay in self.exception_delays.items():
                if isinstance(last_exception, exc_type):
                    base_delay = delay
                    break
        
        # Adapt based on recent failure patterns
        recent_failure_rate = len([f for f in self.recent_failures if time.time() - f < 300]) / 10
        adaptive_factor = 1 + (recent_failure_rate * self.adaptive_multiplier)
        
        return base_delay * adaptive_factor * attempt

# Decorator for easy retry usage
def retry(
    strategy: Optional[RetryStrategy] = None,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    **kwargs
):
    """Decorator to add retry logic to a function"""
    if strategy is None:
        strategy = ExponentialBackoffRetry(
            max_attempts=max_attempts,
            base_delay=base_delay,
            **kwargs
        )
    
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await strategy.execute(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return asyncio.run(strategy.execute(func, *args, **kwargs))
            return sync_wrapper
    
    return decorator

# Global retry strategy registry
_retry_strategies: Dict[str, RetryStrategy] = {}

def get_retry_strategy(name: str, strategy: Optional[RetryStrategy] = None) -> RetryStrategy:
    """Get or create a retry strategy by name"""
    if name not in _retry_strategies:
        if strategy is None:
            strategy = ExponentialBackoffRetry()
        _retry_strategies[name] = strategy
    return _retry_strategies[name]

def get_all_retry_strategies() -> Dict[str, RetryStrategy]:
    """Get all registered retry strategies"""
    return _retry_strategies.copy()

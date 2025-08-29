"""
Performance Metrics Collection

High-performance metrics collection with:
- Real-time performance monitoring
- Minimal overhead data collection
- Automatic performance analysis
- Trend detection and alerting
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import statistics

from ..graph.state import AgentState


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class PerformanceAlert:
    metric_name: str
    threshold: float
    current_value: float
    alert_type: str  # "high", "low", "trend"
    timestamp: float
    message: str


class MetricsCollector:
    """
    High-performance metrics collector for agent system monitoring.
    
    Features:
    - Sub-millisecond metric collection
    - Automatic aggregation and analysis
    - Real-time alerting
    - Minimal memory footprint
    """
    
    def __init__(self, max_points_per_metric: int = 1000):
        self.max_points_per_metric = max_points_per_metric
        self._metrics: Dict[str, deque] = {}
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, List[float]] = {}
        
        # Alert configuration
        self._alert_thresholds: Dict[str, Dict[str, float]] = {}
        self._alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Performance tracking
        self._collection_overhead = deque(maxlen=100)
        
        # Background tasks
        self._cleanup_task = None
        self._analysis_task = None
    
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record a metric point with minimal overhead.
        
        Performance target: <0.1ms per metric
        """
        start_time = time.perf_counter()
        
        try:
            current_time = time.time()
            tags = tags or {}
            
            # Create metric point
            point = MetricPoint(
                name=name,
                value=value,
                timestamp=current_time,
                tags=tags,
                metric_type=metric_type
            )
            
            # Store in appropriate collection
            if metric_type == MetricType.COUNTER:
                self._counters[name] = self._counters.get(name, 0) + value
            elif metric_type == MetricType.GAUGE:
                self._gauges[name] = value
            elif metric_type == MetricType.TIMER:
                if name not in self._timers:
                    self._timers[name] = []
                self._timers[name].append(value)
                # Keep only recent timer values
                if len(self._timers[name]) > 100:
                    self._timers[name] = self._timers[name][-100:]
            
            # Store in time series
            if name not in self._metrics:
                self._metrics[name] = deque(maxlen=self.max_points_per_metric)
            
            self._metrics[name].append(point)
            
            # Check for alerts
            self._check_alerts(name, value)
            
            # Track collection overhead
            collection_time = time.perf_counter() - start_time
            self._collection_overhead.append(collection_time)
            
            # Log slow collections
            if collection_time > 0.001:  # Over 1ms
                print(f"Slow metric collection: {collection_time:.3f}s for {name}")
                
        except Exception as e:
            print(f"Error recording metric {name}: {e}")
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        self.record_metric(name, value, MetricType.COUNTER, tags)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        self.record_metric(name, value, MetricType.GAUGE, tags)
    
    def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timer metric."""
        self.record_metric(name, duration, MetricType.TIMER, tags)
    
    def get_metric_summary(self, name: str, window_seconds: float = 300) -> Dict[str, Any]:
        """Get summary statistics for a metric over a time window."""
        
        if name not in self._metrics:
            return {"error": f"Metric {name} not found"}
        
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        # Filter points within window
        recent_points = [
            point for point in self._metrics[name]
            if point.timestamp >= cutoff_time
        ]
        
        if not recent_points:
            return {"error": f"No recent data for {name}"}
        
        values = [point.value for point in recent_points]
        
        return {
            "metric_name": name,
            "window_seconds": window_seconds,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "latest": values[-1] if values else None,
            "trend": self._calculate_trend(values)
        }
    
    def get_all_metrics_summary(self) -> Dict[str, Any]:
        """Get summary for all metrics."""
        
        summary = {
            "collection_time": time.time(),
            "total_metrics": len(self._metrics),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "collection_overhead": {
                "avg_ms": statistics.mean(self._collection_overhead) * 1000 if self._collection_overhead else 0,
                "max_ms": max(self._collection_overhead) * 1000 if self._collection_overhead else 0
            }
        }
        
        # Add timer summaries
        timer_summaries = {}
        for name, values in self._timers.items():
            if values:
                timer_summaries[name] = {
                    "count": len(values),
                    "avg_ms": statistics.mean(values) * 1000,
                    "p95_ms": self._percentile(values, 95) * 1000,
                    "p99_ms": self._percentile(values, 99) * 1000
                }
        
        summary["timers"] = timer_summaries
        
        return summary
    
    def set_alert_threshold(
        self,
        metric_name: str,
        high_threshold: Optional[float] = None,
        low_threshold: Optional[float] = None
    ):
        """Set alert thresholds for a metric."""
        
        if metric_name not in self._alert_thresholds:
            self._alert_thresholds[metric_name] = {}
        
        if high_threshold is not None:
            self._alert_thresholds[metric_name]["high"] = high_threshold
        
        if low_threshold is not None:
            self._alert_thresholds[metric_name]["low"] = low_threshold
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add callback for performance alerts."""
        self._alert_callbacks.append(callback)
    
    def _check_alerts(self, metric_name: str, value: float):
        """Check if metric value triggers any alerts."""
        
        if metric_name not in self._alert_thresholds:
            return
        
        thresholds = self._alert_thresholds[metric_name]
        current_time = time.time()
        
        # Check high threshold
        if "high" in thresholds and value > thresholds["high"]:
            alert = PerformanceAlert(
                metric_name=metric_name,
                threshold=thresholds["high"],
                current_value=value,
                alert_type="high",
                timestamp=current_time,
                message=f"Metric {metric_name} exceeded high threshold: {value} > {thresholds['high']}"
            )
            self._trigger_alert(alert)
        
        # Check low threshold
        if "low" in thresholds and value < thresholds["low"]:
            alert = PerformanceAlert(
                metric_name=metric_name,
                threshold=thresholds["low"],
                current_value=value,
                alert_type="low",
                timestamp=current_time,
                message=f"Metric {metric_name} below low threshold: {value} < {thresholds['low']}"
            )
            self._trigger_alert(alert)
    
    def _trigger_alert(self, alert: PerformanceAlert):
        """Trigger alert callbacks."""
        
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for values."""
        
        if len(values) < 2:
            return "stable"
        
        # Simple trend calculation
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        if not first_half or not second_half:
            return "stable"
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        change_percent = ((second_avg - first_avg) / first_avg) * 100 if first_avg != 0 else 0
        
        if change_percent > 10:
            return "increasing"
        elif change_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))


class PerformanceTracker:
    """
    Context manager for tracking performance of code blocks.
    
    Usage:
        with PerformanceTracker("agent_execution", metrics_collector):
            # Code to track
            pass
    """
    
    def __init__(
        self,
        operation_name: str,
        metrics_collector: MetricsCollector,
        tags: Optional[Dict[str, str]] = None
    ):
        self.operation_name = operation_name
        self.metrics_collector = metrics_collector
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.perf_counter() - self.start_time
            
            # Record timing metric
            self.metrics_collector.record_timer(
                f"{self.operation_name}_duration",
                duration,
                self.tags
            )
            
            # Record success/failure
            if exc_type is None:
                self.metrics_collector.increment_counter(
                    f"{self.operation_name}_success",
                    1.0,
                    self.tags
                )
            else:
                self.metrics_collector.increment_counter(
                    f"{self.operation_name}_error",
                    1.0,
                    {**self.tags, "error_type": exc_type.__name__}
                )


# Global metrics collector instance
metrics_collector = MetricsCollector()


# Convenience functions
def record_metric(name: str, value: float, metric_type: MetricType = MetricType.GAUGE, tags: Optional[Dict[str, str]] = None):
    """Record a metric using the global collector."""
    metrics_collector.record_metric(name, value, metric_type, tags)


def increment_counter(name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
    """Increment a counter using the global collector."""
    metrics_collector.increment_counter(name, value, tags)


def set_gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Set a gauge using the global collector."""
    metrics_collector.set_gauge(name, value, tags)


def record_timer(name: str, duration: float, tags: Optional[Dict[str, str]] = None):
    """Record a timer using the global collector."""
    metrics_collector.record_timer(name, duration, tags)


def track_performance(operation_name: str, tags: Optional[Dict[str, str]] = None) -> PerformanceTracker:
    """Create a performance tracker context manager."""
    return PerformanceTracker(operation_name, metrics_collector, tags)


# Default alert callback
def default_alert_callback(alert: PerformanceAlert):
    """Default alert callback that prints alerts."""
    print(f"🚨 PERFORMANCE ALERT: {alert.message}")


# Set up default alerting
metrics_collector.add_alert_callback(default_alert_callback)

# Set up common alert thresholds
metrics_collector.set_alert_threshold("agent_execution_duration", high_threshold=5.0)  # 5 seconds
metrics_collector.set_alert_threshold("cache_hit_rate", low_threshold=0.7)  # 70%
metrics_collector.set_alert_threshold("error_rate", high_threshold=0.1)  # 10%

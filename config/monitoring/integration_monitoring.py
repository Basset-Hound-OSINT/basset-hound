"""
Integration Monitoring Implementation for basset-hound + basset-verify.

Provides real-time monitoring, metrics collection, and alerting for the
integration between basset-hound and basset-verify.

Phase 7.3 - Production Integration Monitoring
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import defaultdict
from statistics import mean, median, quantiles

import httpx

logger = logging.getLogger("basset_hound.monitoring.integration")


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert definition and trigger."""
    name: str
    severity: AlertSeverity
    message: str
    triggered_at: datetime
    metric_name: str
    metric_value: float
    threshold: float


class MetricsCollector:
    """Collects metrics for integration monitoring."""

    def __init__(self, window_size: int = 3600):
        """
        Initialize metrics collector.

        Args:
            window_size: Time window in seconds for metrics (default 1 hour)
        """
        self.window_size = window_size
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.alerts: List[Alert] = []
        self._lock = asyncio.Lock()

    async def record_verification(
        self,
        identifier_type: str,
        status: str,
        response_time_ms: float,
        cached: bool = False,
    ):
        """Record a verification metric."""
        async with self._lock:
            # Response time
            key = f"verification_response_time_{identifier_type}"
            self.metrics[key].append(
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    value=response_time_ms,
                    labels={"type": identifier_type, "cached": str(cached)},
                )
            )

            # Success/error
            success_key = f"verification_status_{identifier_type}_{status}"
            self.metrics[success_key].append(
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    value=1.0,
                    labels={"type": identifier_type, "status": status},
                )
            )

            # Cache hit
            if cached:
                cache_key = f"verification_cache_hit_{identifier_type}"
                self.metrics[cache_key].append(
                    MetricPoint(
                        timestamp=datetime.utcnow(),
                        value=1.0,
                        labels={"type": identifier_type},
                    )
                )

            self._cleanup_old_metrics()

    async def record_service_health(
        self,
        service_name: str,
        healthy: bool,
        response_time_ms: float,
    ):
        """Record service health metric."""
        async with self._lock:
            key = f"service_health_{service_name}"
            self.metrics[key].append(
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    value=1.0 if healthy else 0.0,
                    labels={"service": service_name},
                )
            )

            latency_key = f"service_latency_{service_name}"
            self.metrics[latency_key].append(
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    value=response_time_ms,
                    labels={"service": service_name},
                )
            )

            self._cleanup_old_metrics()

    async def record_fallback_activation(self, identifier_type: str):
        """Record fallback activation."""
        async with self._lock:
            key = "fallback_activation"
            self.metrics[key].append(
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    value=1.0,
                    labels={"type": identifier_type},
                )
            )
            self._cleanup_old_metrics()

    def _cleanup_old_metrics(self):
        """Remove metrics older than window size."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.window_size)

        for key in self.metrics:
            self.metrics[key] = [
                m for m in self.metrics[key]
                if m.timestamp > cutoff_time
            ]

    def get_metric_stats(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a metric."""
        if metric_name not in self.metrics:
            return None

        points = self.metrics[metric_name]
        if not points:
            return None

        values = [p.value for p in points]

        return {
            "metric": metric_name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": mean(values),
            "median": median(values),
            "p95": quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
            "p99": quantiles(values, n=100)[98] if len(values) >= 100 else max(values),
            "latest": values[-1] if values else None,
        }

    def get_success_rate(self, identifier_type: str) -> float:
        """Get success rate for identifier type."""
        valid_metrics = [
            m for key in self.metrics
            if f"verification_status_{identifier_type}_valid" in key
            for m in self.metrics[key]
        ]
        invalid_metrics = [
            m for key in self.metrics
            if f"verification_status_{identifier_type}_invalid" in key
            for m in self.metrics[key]
        ]
        error_metrics = [
            m for key in self.metrics
            if f"verification_status_{identifier_type}_error" in key
            for m in self.metrics[key]
        ]

        total = len(valid_metrics) + len(invalid_metrics) + len(error_metrics)
        if total == 0:
            return 0.0

        return (len(valid_metrics) / total) * 100

    def get_cache_hit_rate(self, identifier_type: str) -> float:
        """Get cache hit rate for identifier type."""
        total_metrics = [
            m for key in self.metrics
            if f"verification_response_time_{identifier_type}" in key
            for m in self.metrics[key]
        ]
        cache_hit_metrics = [
            m for key in self.metrics
            if f"verification_cache_hit_{identifier_type}" in key
            for m in self.metrics[key]
        ]

        if not total_metrics:
            return 0.0

        return (len(cache_hit_metrics) / len(total_metrics)) * 100

    def get_error_rate(self) -> float:
        """Get overall error rate."""
        error_count = sum(
            len(points) for key, points in self.metrics.items()
            if "status_error" in key
        )
        total_count = sum(
            len(points) for key, points in self.metrics.items()
            if "verification_status" in key
        )

        if total_count == 0:
            return 0.0

        return (error_count / total_count) * 100

    def get_fallback_rate(self) -> float:
        """Get fallback activation rate."""
        fallback_count = sum(
            len(points) for key, points in self.metrics.items()
            if "fallback_activation" in key
        )
        total_count = sum(
            len(points) for key, points in self.metrics.items()
            if "verification_status" in key
        )

        if total_count == 0:
            return 0.0

        return (fallback_count / total_count) * 100


class HealthChecker:
    """Checks health of basset-verify and basset-hound services."""

    def __init__(
        self,
        basset_verify_url: str = "http://basset_verify:8001",
        basset_hound_url: str = "http://basset_api:8000",
        timeout: float = 10.0,
    ):
        """Initialize health checker."""
        self.basset_verify_url = basset_verify_url
        self.basset_hound_url = basset_hound_url
        self.timeout = timeout
        self.last_check: Dict[str, Dict[str, Any]] = {}

    async def check_basset_verify(self) -> Dict[str, Any]:
        """Check basset-verify health."""
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.basset_verify_url}/health")
                response_time = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "service": "basset_verify",
                        "healthy": True,
                        "status": data.get("status", "healthy"),
                        "version": data.get("version"),
                        "response_time_ms": response_time,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
        except Exception as e:
            logger.warning(f"basset-verify health check failed: {e}")

        return {
            "service": "basset_verify",
            "healthy": False,
            "status": "unreachable",
            "error": str(e) if 'e' in locals() else "Unknown error",
            "response_time_ms": None,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def check_basset_hound(self) -> Dict[str, Any]:
        """Check basset-hound health."""
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.basset_hound_url}/health")
                response_time = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "service": "basset_hound",
                        "healthy": True,
                        "status": data.get("status", "healthy"),
                        "version": data.get("version"),
                        "response_time_ms": response_time,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
        except Exception as e:
            logger.warning(f"basset-hound health check failed: {e}")

        return {
            "service": "basset_hound",
            "healthy": False,
            "status": "unreachable",
            "error": str(e) if 'e' in locals() else "Unknown error",
            "response_time_ms": None,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all services."""
        verify_health, hound_health = await asyncio.gather(
            self.check_basset_verify(),
            self.check_basset_hound(),
        )

        self.last_check["basset_verify"] = verify_health
        self.last_check["basset_hound"] = hound_health

        return {
            "basset_verify": verify_health,
            "basset_hound": hound_health,
            "timestamp": datetime.utcnow().isoformat(),
        }


class AlertManager:
    """Manages alerts based on monitoring data."""

    def __init__(self, metrics: MetricsCollector):
        """Initialize alert manager."""
        self.metrics = metrics
        self.active_alerts: List[Alert] = []

    def check_alerts(self) -> List[Alert]:
        """Check and trigger alerts based on current metrics."""
        new_alerts = []

        # Check error rate
        error_rate = self.metrics.get_error_rate()
        if error_rate > 5.0:
            alert = Alert(
                name="high_error_rate",
                severity=AlertSeverity.WARNING if error_rate < 10 else AlertSeverity.CRITICAL,
                message=f"Verification error rate is {error_rate:.1f}%",
                triggered_at=datetime.utcnow(),
                metric_name="verification_error_rate",
                metric_value=error_rate,
                threshold=5.0,
            )
            new_alerts.append(alert)

        # Check fallback rate
        fallback_rate = self.metrics.get_fallback_rate()
        if fallback_rate > 0.1:
            alert = Alert(
                name="fallback_activated",
                severity=AlertSeverity.WARNING,
                message=f"Fallback verification activated ({fallback_rate:.2f}%)",
                triggered_at=datetime.utcnow(),
                metric_name="fallback_activation_rate",
                metric_value=fallback_rate,
                threshold=0.0,
            )
            new_alerts.append(alert)

        # Check response time
        response_time_stats = self.metrics.get_metric_stats(
            "verification_response_time_email"
        )
        if response_time_stats and response_time_stats.get("p95", 0) > 2000:
            alert = Alert(
                name="high_latency",
                severity=AlertSeverity.WARNING,
                message=f"Verification latency high (p95: {response_time_stats['p95']:.0f}ms)",
                triggered_at=datetime.utcnow(),
                metric_name="verification_response_time_p95",
                metric_value=response_time_stats["p95"],
                threshold=2000.0,
            )
            new_alerts.append(alert)

        self.active_alerts = new_alerts
        return new_alerts


class IntegrationMonitor:
    """Main integration monitoring class."""

    def __init__(
        self,
        basset_verify_url: str = "http://basset_verify:8001",
        basset_hound_url: str = "http://basset_api:8000",
        check_interval: int = 30,
    ):
        """Initialize integration monitor."""
        self.metrics = MetricsCollector()
        self.health_checker = HealthChecker(
            basset_verify_url=basset_verify_url,
            basset_hound_url=basset_hound_url,
        )
        self.alert_manager = AlertManager(self.metrics)
        self.check_interval = check_interval
        self._running = False

    async def start(self):
        """Start continuous monitoring."""
        self._running = True
        logger.info("Starting integration monitoring...")

        while self._running:
            try:
                # Check health
                health = await self.health_checker.check_all()

                # Record metrics
                basset_verify = health.get("basset_verify", {})
                await self.metrics.record_service_health(
                    "basset_verify",
                    basset_verify.get("healthy", False),
                    basset_verify.get("response_time_ms", 0) or 0,
                )

                basset_hound = health.get("basset_hound", {})
                await self.metrics.record_service_health(
                    "basset_hound",
                    basset_hound.get("healthy", False),
                    basset_hound.get("response_time_ms", 0) or 0,
                )

                # Check alerts
                alerts = self.alert_manager.check_alerts()
                if alerts:
                    for alert in alerts:
                        logger.warning(
                            f"ALERT [{alert.severity.value}] {alert.name}: {alert.message}"
                        )

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in integration monitoring: {e}")
                await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop monitoring."""
        self._running = False
        logger.info("Stopping integration monitoring...")

    def get_status(self) -> Dict[str, Any]:
        """Get current integration status."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health": self.health_checker.last_check,
            "metrics": {
                "error_rate": self.metrics.get_error_rate(),
                "fallback_rate": self.metrics.get_fallback_rate(),
                "success_rates": {
                    "email": self.metrics.get_success_rate("email"),
                    "phone": self.metrics.get_success_rate("phone"),
                    "crypto_address": self.metrics.get_success_rate("crypto_address"),
                    "domain": self.metrics.get_success_rate("domain"),
                    "ip_address": self.metrics.get_success_rate("ip_address"),
                    "url": self.metrics.get_success_rate("url"),
                    "username": self.metrics.get_success_rate("username"),
                },
                "cache_hit_rates": {
                    "email": self.metrics.get_cache_hit_rate("email"),
                    "phone": self.metrics.get_cache_hit_rate("phone"),
                    "crypto_address": self.metrics.get_cache_hit_rate("crypto_address"),
                    "domain": self.metrics.get_cache_hit_rate("domain"),
                    "ip_address": self.metrics.get_cache_hit_rate("ip_address"),
                    "url": self.metrics.get_cache_hit_rate("url"),
                    "username": self.metrics.get_cache_hit_rate("username"),
                },
            },
            "alerts": [
                {
                    "name": a.name,
                    "severity": a.severity.value,
                    "message": a.message,
                    "metric": a.metric_name,
                    "value": a.metric_value,
                    "threshold": a.threshold,
                    "triggered_at": a.triggered_at.isoformat(),
                }
                for a in self.alert_manager.active_alerts
            ],
        }


# Global monitor instance
_monitor: Optional[IntegrationMonitor] = None


def get_integration_monitor() -> IntegrationMonitor:
    """Get or create the global integration monitor."""
    global _monitor
    if _monitor is None:
        _monitor = IntegrationMonitor()
    return _monitor


async def start_monitoring():
    """Start the global integration monitor."""
    monitor = get_integration_monitor()
    await monitor.start()


async def stop_monitoring():
    """Stop the global integration monitor."""
    monitor = get_integration_monitor()
    await monitor.stop()

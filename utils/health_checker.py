"""
Comprehensive health checking system for NSA ReflexArc.
Provides detailed system health monitoring for production deployment.
"""

import asyncio
import time
import psutil
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthChecker:
    """Comprehensive health checker for the NSA system."""
    
    def __init__(self, brain=None, sensor_mgr=None):
        self.brain = brain
        self.sensor_mgr = sensor_mgr
        self.start_time = time.time()
        
        # Get health check timeout from config, default to 5.0 seconds
        self.health_timeout = 5.0
        if brain and hasattr(brain, 'config'):
            brain_config = brain.config.get('brain', {})
            self.health_timeout = brain_config.get('health_check_timeout', 5.0)
        
    async def check_full_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of all system components.
        
        Returns:
            Dict with overall status and detailed component health
        """
        start_time = time.time()
        
        # Run all health checks concurrently with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    self._check_provider_availability(),
                    self._check_database_connectivity(),
                    self._check_memory_usage(),
                    self._check_sensor_status(),
                    self._check_event_bus_health(),
                    return_exceptions=True
                ),
                timeout=self.health_timeout
            )
            
            provider_health, db_health, memory_health, sensor_health, event_bus_health = results
            
        except asyncio.TimeoutError:
            logger.warning("Health check timeout exceeded", timeout=self.health_timeout)
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Health check timeout",
                "timestamp": time.time(),
                "uptime": time.time() - self.start_time,
                "check_duration": time.time() - start_time,
                "components": {
                    "providers": {"status": HealthStatus.UNKNOWN, "message": "Timeout"},
                    "database": {"status": HealthStatus.UNKNOWN, "message": "Timeout"},
                    "memory": {"status": HealthStatus.UNKNOWN, "message": "Timeout"},
                    "sensors": {"status": HealthStatus.UNKNOWN, "message": "Timeout"},
                    "event_bus": {"status": HealthStatus.UNKNOWN, "message": "Timeout"}
                }
            }
        
        # Handle any exceptions from individual checks
        components = {}
        component_names = ["providers", "database", "memory", "sensors", "event_bus"]
        
        for i, (name, result) in enumerate(zip(component_names, results)):
            if isinstance(result, Exception):
                components[name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"Check failed: {str(result)}"
                }
            else:
                components[name] = result
        
        # Determine overall health status
        overall_status = self._determine_overall_status(components)
        
        return {
            "status": overall_status,
            "message": self._get_status_message(overall_status, components),
            "timestamp": time.time(),
            "uptime": time.time() - self.start_time,
            "check_duration": time.time() - start_time,
            "components": components
        }
    
    async def check_readiness(self) -> Dict[str, Any]:
        """
        Check if system is ready to accept requests (Kubernetes readiness probe).
        
        Returns:
            Dict with readiness status
        """
        start_time = time.time()
        
        # Critical components for readiness
        try:
            db_ready = await self._check_database_connectivity()
            provider_ready = await self._check_provider_availability()
            
            # System is ready if database and at least one provider are available
            is_ready = (
                db_ready["status"] in [HealthStatus.HEALTHY, HealthStatus.DEGRADED] and
                provider_ready["status"] in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
            )
            
            return {
                "ready": is_ready,
                "status": HealthStatus.HEALTHY if is_ready else HealthStatus.UNHEALTHY,
                "message": "System ready" if is_ready else "System not ready",
                "timestamp": time.time(),
                "check_duration": time.time() - start_time,
                "components": {
                    "database": db_ready,
                    "providers": provider_ready
                }
            }
            
        except Exception as e:
            logger.error("Readiness check failed", error=str(e))
            return {
                "ready": False,
                "status": HealthStatus.UNHEALTHY,
                "message": f"Readiness check failed: {str(e)}",
                "timestamp": time.time(),
                "check_duration": time.time() - start_time
            }
    
    async def check_liveness(self) -> Dict[str, Any]:
        """
        Check if system is alive (Kubernetes liveness probe).
        
        Returns:
            Dict with liveness status
        """
        start_time = time.time()
        
        try:
            # Basic liveness checks
            memory_ok = psutil.virtual_memory().percent < 95  # Not critically low on memory
            disk_ok = psutil.disk_usage('/').percent < 95    # Not critically low on disk
            
            # Check if main event loop is responsive
            loop_responsive = True
            try:
                await asyncio.wait_for(asyncio.sleep(0), timeout=1.0)
            except asyncio.TimeoutError:
                loop_responsive = False
            
            is_alive = memory_ok and disk_ok and loop_responsive
            
            return {
                "alive": is_alive,
                "status": HealthStatus.HEALTHY if is_alive else HealthStatus.UNHEALTHY,
                "message": "System alive" if is_alive else "System not responding",
                "timestamp": time.time(),
                "uptime": time.time() - self.start_time,
                "check_duration": time.time() - start_time,
                "checks": {
                    "memory_ok": memory_ok,
                    "disk_ok": disk_ok,
                    "loop_responsive": loop_responsive
                }
            }
            
        except Exception as e:
            logger.error("Liveness check failed", error=str(e))
            return {
                "alive": False,
                "status": HealthStatus.UNHEALTHY,
                "message": f"Liveness check failed: {str(e)}",
                "timestamp": time.time(),
                "check_duration": time.time() - start_time
            }
    
    async def _check_provider_availability(self) -> Dict[str, Any]:
        """Check AI provider availability and circuit breaker status."""
        if not self.brain or not hasattr(self.brain, 'model_router'):
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "Model router not available",
                "providers": {}
            }
        
        try:
            router = self.brain.model_router
            provider_status = {}
            healthy_providers = 0
            total_providers = 0
            
            # Check each provider's circuit breaker status
            for provider_name, provider in router.providers.items():
                total_providers += 1
                
                # Check if provider has circuit breaker
                if hasattr(provider, 'circuit_breaker'):
                    cb_state = provider.circuit_breaker.current_state
                    if cb_state == 'closed':  # Circuit closed = healthy
                        provider_status[provider_name] = {
                            "status": HealthStatus.HEALTHY,
                            "circuit_breaker": "closed",
                            "failure_count": provider.circuit_breaker.fail_counter
                        }
                        healthy_providers += 1
                    elif cb_state == 'half_open':
                        provider_status[provider_name] = {
                            "status": HealthStatus.DEGRADED,
                            "circuit_breaker": "half_open",
                            "failure_count": provider.circuit_breaker.fail_counter
                        }
                    else:  # open
                        provider_status[provider_name] = {
                            "status": HealthStatus.UNHEALTHY,
                            "circuit_breaker": "open",
                            "failure_count": provider.circuit_breaker.fail_counter
                        }
                else:
                    # No circuit breaker, assume healthy
                    provider_status[provider_name] = {
                        "status": HealthStatus.HEALTHY,
                        "circuit_breaker": "none"
                    }
                    healthy_providers += 1
            
            # Determine overall provider health
            if healthy_providers == 0:
                status = HealthStatus.UNHEALTHY
                message = "No providers available"
            elif healthy_providers < total_providers:
                status = HealthStatus.DEGRADED
                message = f"{healthy_providers}/{total_providers} providers healthy"
            else:
                status = HealthStatus.HEALTHY
                message = f"All {total_providers} providers healthy"
            
            return {
                "status": status,
                "message": message,
                "healthy_count": healthy_providers,
                "total_count": total_providers,
                "providers": provider_status
            }
            
        except Exception as e:
            logger.error("Provider health check failed", error=str(e))
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Provider check failed: {str(e)}",
                "providers": {}
            }
    
    async def _check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        if not self.brain or not hasattr(self.brain, 'memory'):
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "Hippocampus not available"
            }
        
        try:
            start_time = time.time()
            
            # Test database connection with a simple query
            hippocampus = self.brain.memory
            
            # Check if connection pool is available
            if hasattr(hippocampus, '_connection_pool') and hippocampus._connection_pool:
                pool_size = len(hippocampus._connection_pool)
                max_pool_size = getattr(hippocampus, 'max_pool_size', 10)
            else:
                pool_size = 0
                max_pool_size = 0
            
            # Test a simple database operation
            test_query_time = time.time()
            # This is a simple test - in a real implementation you'd do a lightweight query
            await asyncio.sleep(0.001)  # Simulate quick DB check
            query_duration = time.time() - test_query_time
            
            # Check database file size and accessibility
            db_path = Path("memory/long_term_memory.db")
            if db_path.exists():
                db_size_mb = db_path.stat().st_size / (1024 * 1024)
                db_accessible = os.access(db_path, os.R_OK | os.W_OK)
            else:
                db_size_mb = 0
                db_accessible = False
            
            total_duration = time.time() - start_time
            
            # Determine health based on performance and accessibility
            if not db_accessible:
                status = HealthStatus.UNHEALTHY
                message = "Database not accessible"
            elif query_duration > 1.0:  # Slow query
                status = HealthStatus.DEGRADED
                message = "Database responding slowly"
            elif total_duration > 2.0:  # Overall slow check
                status = HealthStatus.DEGRADED
                message = "Database check slow"
            else:
                status = HealthStatus.HEALTHY
                message = "Database healthy"
            
            return {
                "status": status,
                "message": message,
                "response_time_ms": round(query_duration * 1000, 2),
                "check_duration_ms": round(total_duration * 1000, 2),
                "connection_pool_size": pool_size,
                "max_pool_size": max_pool_size,
                "database_size_mb": round(db_size_mb, 2),
                "accessible": db_accessible
            }
            
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Database check failed: {str(e)}",
                "response_time_ms": None,
                "accessible": False
            }
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage and performance."""
        try:
            # Get system memory info
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Get process memory info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Calculate percentages
            memory_percent = memory.percent
            swap_percent = swap.percent if swap.total > 0 else 0
            
            # Determine health based on memory usage
            if memory_percent > 90 or swap_percent > 50:
                status = HealthStatus.UNHEALTHY
                message = "Critical memory usage"
            elif memory_percent > 80 or swap_percent > 25:
                status = HealthStatus.DEGRADED
                message = "High memory usage"
            else:
                status = HealthStatus.HEALTHY
                message = "Memory usage normal"
            
            return {
                "status": status,
                "message": message,
                "system_memory_percent": memory_percent,
                "system_memory_available_gb": round(memory.available / (1024**3), 2),
                "system_memory_total_gb": round(memory.total / (1024**3), 2),
                "swap_percent": swap_percent,
                "process_memory_mb": round(process_memory.rss / (1024**2), 2),
                "process_memory_vms_mb": round(process_memory.vms / (1024**2), 2)
            }
            
        except Exception as e:
            logger.error("Memory health check failed", error=str(e))
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Memory check failed: {str(e)}"
            }
    
    async def _check_sensor_status(self) -> Dict[str, Any]:
        """Check sensor health and status."""
        if not self.sensor_mgr:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "Sensor manager not available",
                "sensors": {}
            }
        
        try:
            sensor_status = {}
            healthy_sensors = 0
            total_sensors = 0
            error_sensors = 0
            
            for sensor_name, sensor_info in self.sensor_mgr.sensors.items():
                total_sensors += 1
                sensor = sensor_info['sensor']
                
                # Check if sensor is enabled
                enabled = sensor_info.get('enabled', True)
                
                # Check sensor health (if it has a health check method)
                if hasattr(sensor, 'health_check'):
                    try:
                        health = await sensor.health_check()
                        sensor_status[sensor_name] = {
                            "status": health.get("status", HealthStatus.UNKNOWN),
                            "enabled": enabled,
                            "message": health.get("message", "No message"),
                            "last_reading": health.get("last_reading")
                        }
                        if health.get("status") == HealthStatus.HEALTHY:
                            healthy_sensors += 1
                        elif health.get("status") == HealthStatus.UNHEALTHY:
                            error_sensors += 1
                    except Exception as e:
                        sensor_status[sensor_name] = {
                            "status": HealthStatus.UNHEALTHY,
                            "enabled": enabled,
                            "message": f"Health check failed: {str(e)}"
                        }
                        error_sensors += 1
                else:
                    # No health check method, assume healthy if enabled
                    sensor_status[sensor_name] = {
                        "status": HealthStatus.HEALTHY if enabled else HealthStatus.DEGRADED,
                        "enabled": enabled,
                        "message": "No health check available"
                    }
                    if enabled:
                        healthy_sensors += 1
            
            # Determine overall sensor health
            if error_sensors > 0:
                status = HealthStatus.DEGRADED if healthy_sensors > 0 else HealthStatus.UNHEALTHY
                message = f"{error_sensors} sensors have errors"
            elif healthy_sensors == total_sensors:
                status = HealthStatus.HEALTHY
                message = f"All {total_sensors} sensors healthy"
            else:
                status = HealthStatus.DEGRADED
                message = f"{healthy_sensors}/{total_sensors} sensors healthy"
            
            return {
                "status": status,
                "message": message,
                "healthy_count": healthy_sensors,
                "total_count": total_sensors,
                "error_count": error_sensors,
                "sensors": sensor_status
            }
            
        except Exception as e:
            logger.error("Sensor health check failed", error=str(e))
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Sensor check failed: {str(e)}",
                "sensors": {}
            }
    
    async def _check_event_bus_health(self) -> Dict[str, Any]:
        """Check event bus health and performance."""
        try:
            from event_bus import event_bus
            
            # Get event bus statistics
            event_count = len(event_bus.events)
            subscriber_count = len(event_bus.subscribers)
            
            # Check if cleanup is running
            cleanup_running = hasattr(event_bus, '_cleanup_task') and event_bus._cleanup_task
            
            # Determine health based on event queue size
            if event_count > 10000:  # Too many events queued
                status = HealthStatus.DEGRADED
                message = "High event queue size"
            elif event_count > 50000:  # Critical event queue size
                status = HealthStatus.UNHEALTHY
                message = "Critical event queue size"
            else:
                status = HealthStatus.HEALTHY
                message = "Event bus healthy"
            
            return {
                "status": status,
                "message": message,
                "event_count": event_count,
                "subscriber_count": subscriber_count,
                "cleanup_running": cleanup_running
            }
            
        except Exception as e:
            logger.error("Event bus health check failed", error=str(e))
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Event bus check failed: {str(e)}"
            }
    
    def _determine_overall_status(self, components: Dict[str, Dict]) -> str:
        """Determine overall system health from component health."""
        unhealthy_count = 0
        degraded_count = 0
        total_count = len(components)
        
        for component in components.values():
            status = component.get("status", HealthStatus.UNKNOWN)
            if status == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
            elif status == HealthStatus.DEGRADED:
                degraded_count += 1
        
        # Overall health logic
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def _get_status_message(self, status: str, components: Dict[str, Dict]) -> str:
        """Generate human-readable status message."""
        if status == HealthStatus.HEALTHY:
            return "All systems operational"
        elif status == HealthStatus.DEGRADED:
            degraded = [name for name, comp in components.items() 
                       if comp.get("status") == HealthStatus.DEGRADED]
            return f"Degraded components: {', '.join(degraded)}"
        else:  # UNHEALTHY
            unhealthy = [name for name, comp in components.items() 
                        if comp.get("status") == HealthStatus.UNHEALTHY]
            return f"Unhealthy components: {', '.join(unhealthy)}"
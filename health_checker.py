"""
Health check module for the hybrid search API.
Provides comprehensive health monitoring and diagnostics.
"""
import asyncio
import time
import psutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    response_time: float
    details: Dict[str, Any]
    timestamp: datetime


class HealthChecker:
    """Comprehensive health checker."""
    
    def __init__(self):
        self.checks: List[callable] = []
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks."""
        self.checks.extend([
            self._check_system_resources,
            self._check_database_connection,
            self._check_llm_service,
            self._check_wordpress_connection,
            self._check_search_system,
            self._check_connection_pools,
        ])
    
    async def _check_system_resources(self) -> HealthCheck:
        """Check system resource usage."""
        start_time = time.time()
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Determine status
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "System resources critically high"
            elif cpu_percent > 80 or memory_percent > 80 or disk_percent > 80:
                status = HealthStatus.DEGRADED
                message = "System resources high"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_free_gb": round(disk.free / (1024**3), 2),
                },
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"System resources check failed: {e}")
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNKNOWN,
                message=f"System resources check failed: {str(e)}",
                response_time=time.time() - start_time,
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _check_database_connection(self) -> HealthCheck:
        """Check database connection."""
        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from qdrant_manager import QdrantManager
            
            qdrant_manager = QdrantManager()
            collection_info = qdrant_manager.get_collection_info()
            
            if collection_info:
                status = HealthStatus.HEALTHY
                message = "Database connection healthy"
                details = collection_info
            else:
                status = HealthStatus.DEGRADED
                message = "Database connection degraded"
                details = {"error": "No collection info"}
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="database",
                status=status,
                message=message,
                response_time=response_time,
                details=details,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time=time.time() - start_time,
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _check_llm_service(self) -> HealthCheck:
        """Check LLM service connection."""
        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from cerebras_llm import CerebrasLLM
            
            llm_client = CerebrasLLM()
            is_healthy = llm_client.test_connection()
            
            if is_healthy:
                status = HealthStatus.HEALTHY
                message = "LLM service healthy"
                details = {"model": llm_client.model}
            else:
                status = HealthStatus.DEGRADED
                message = "LLM service degraded"
                details = {"error": "Connection test failed"}
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="llm_service",
                status=status,
                message=message,
                response_time=response_time,
                details=details,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"LLM service check failed: {e}")
            return HealthCheck(
                name="llm_service",
                status=HealthStatus.UNHEALTHY,
                message=f"LLM service failed: {str(e)}",
                response_time=time.time() - start_time,
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _check_wordpress_connection(self) -> HealthCheck:
        """Check WordPress connection."""
        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from wordpress_client import WordPressContentFetcher
            
            wp_client = WordPressContentFetcher()
            
            # Test with a simple request
            test_url = wp_client.base_url.replace('/wp-json/wp/v2', '')
            
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{test_url}/wp-json/wp/v2/")
                
                if response.status_code == 200:
                    status = HealthStatus.HEALTHY
                    message = "WordPress connection healthy"
                    details = {"base_url": wp_client.base_url}
                else:
                    status = HealthStatus.DEGRADED
                    message = f"WordPress connection degraded (status: {response.status_code})"
                    details = {"status_code": response.status_code}
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="wordpress",
                status=status,
                message=message,
                response_time=response_time,
                details=details,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"WordPress check failed: {e}")
            return HealthCheck(
                name="wordpress",
                status=HealthStatus.UNHEALTHY,
                message=f"WordPress connection failed: {str(e)}",
                response_time=time.time() - start_time,
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _check_search_system(self) -> HealthCheck:
        """Check search system."""
        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from simple_hybrid_search import SimpleHybridSearch
            
            search_system = SimpleHybridSearch()
            stats = search_system.get_stats()
            
            if stats and stats.get('total_documents', 0) > 0:
                status = HealthStatus.HEALTHY
                message = "Search system healthy"
                details = stats
            else:
                status = HealthStatus.DEGRADED
                message = "Search system degraded (no documents indexed)"
                details = stats or {}
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="search_system",
                status=status,
                message=message,
                response_time=response_time,
                details=details,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Search system check failed: {e}")
            return HealthCheck(
                name="search_system",
                status=HealthStatus.UNHEALTHY,
                message=f"Search system failed: {str(e)}",
                response_time=time.time() - start_time,
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _check_connection_pools(self) -> HealthCheck:
        """Check connection pools."""
        start_time = time.time()
        
        try:
            from connection_manager import connection_manager
            
            stats = connection_manager.get_stats()
            
            if stats['active_pools'] > 0:
                status = HealthStatus.HEALTHY
                message = "Connection pools healthy"
                details = stats
            else:
                status = HealthStatus.DEGRADED
                message = "No active connection pools"
                details = stats
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                name="connection_pools",
                status=status,
                message=message,
                response_time=response_time,
                details=details,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Connection pools check failed: {e}")
            return HealthCheck(
                name="connection_pools",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection pools failed: {str(e)}",
                response_time=time.time() - start_time,
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        start_time = time.time()
        
        # Run checks concurrently
        check_tasks = [check() for check in self.checks]
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        checks = []
        overall_status = HealthStatus.HEALTHY
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
                checks.append(HealthCheck(
                    name="unknown",
                    status=HealthStatus.UNKNOWN,
                    message=f"Check failed: {str(result)}",
                    response_time=0,
                    details={"error": str(result)},
                    timestamp=datetime.utcnow()
                ))
                overall_status = HealthStatus.UNHEALTHY
            else:
                checks.append(result)
                # Determine overall status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        total_time = time.time() - start_time
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "total_check_time": round(total_time, 3),
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "response_time": round(check.response_time, 3),
                    "details": check.details,
                    "timestamp": check.timestamp.isoformat()
                }
                for check in checks
            ]
        }
    
    def add_custom_check(self, check_func: callable):
        """Add a custom health check."""
        self.checks.append(check_func)


# Global health checker instance
health_checker = HealthChecker()


async def get_health_status() -> Dict[str, Any]:
    """Get comprehensive health status."""
    return await health_checker.run_all_checks()


async def get_quick_health_status() -> Dict[str, Any]:
    """Get quick health status (basic checks only)."""
    try:
        # Quick system check
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
        if cpu_percent > 90 or memory_percent > 90:
            status = "unhealthy"
        elif cpu_percent > 80 or memory_percent > 80:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "quick_check": True,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent
        }
        
    except Exception as e:
        logger.error(f"Quick health check failed: {e}")
        return {
            "status": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }





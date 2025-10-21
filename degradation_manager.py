"""
Graceful degradation module for the hybrid search API.
Provides fallback mechanisms when services are unavailable.
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Service health information."""
    name: str
    status: ServiceStatus
    last_check: datetime
    error_count: int
    last_error: Optional[str]
    response_time: float


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                return True
            return False
        
        if self.state == "half-open":
            return True
        
        return False
    
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self, error: str):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened due to {self.failure_count} failures: {error}")


class GracefulDegradationManager:
    """Manages graceful degradation across services."""
    
    def __init__(self):
        self.service_health: Dict[str, ServiceHealth] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.fallback_responses: Dict[str, Any] = {}
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Initialize default service configurations."""
        services = ['qdrant', 'llm_service', 'wordpress', 'search_system']
        
        for service in services:
            self.service_health[service] = ServiceHealth(
                name=service,
                status=ServiceStatus.UNKNOWN,
                last_check=datetime.utcnow(),
                error_count=0,
                last_error=None,
                response_time=0.0
            )
            self.circuit_breakers[service] = CircuitBreaker()
    
    def update_service_health(self, service: str, status: ServiceStatus, 
                            response_time: float = 0.0, error: str = None):
        """Update service health status."""
        if service not in self.service_health:
            self.service_health[service] = ServiceHealth(
                name=service,
                status=status,
                last_check=datetime.utcnow(),
                error_count=0,
                last_error=None,
                response_time=response_time
            )
        
        health = self.service_health[service]
        health.status = status
        health.last_check = datetime.utcnow()
        health.response_time = response_time
        
        if error:
            health.error_count += 1
            health.last_error = error
            self.circuit_breakers[service].record_failure(error)
        else:
            self.circuit_breakers[service].record_success()
    
    def is_service_available(self, service: str) -> bool:
        """Check if service is available."""
        if service not in self.circuit_breakers:
            return True
        
        return self.circuit_breakers[service].can_execute()
    
    def get_fallback_response(self, operation: str, query: str = None) -> Dict[str, Any]:
        """Get fallback response for failed operations."""
        if operation == "search":
            return self._get_search_fallback(query)
        elif operation == "index":
            return self._get_index_fallback()
        elif operation == "answer":
            return self._get_answer_fallback()
        else:
            return {"error": "Service temporarily unavailable"}
    
    def _get_search_fallback(self, query: str = None) -> Dict[str, Any]:
        """Get fallback search response."""
        return {
            "success": True,
            "results": [],
            "metadata": {
                "query": query or "",
                "total_results": 0,
                "response_time": 0,
                "has_answer": False,
                "answer": "",
                "fallback_mode": True,
                "message": "Search service is temporarily unavailable. Please try again later."
            },
            "fallback": True
        }
    
    def _get_index_fallback(self) -> Dict[str, Any]:
        """Get fallback index response."""
        return {
            "success": False,
            "message": "Indexing service is temporarily unavailable. Please try again later.",
            "indexed_count": 0,
            "total_count": 0,
            "processing_time": 0,
            "fallback": True
        }
    
    def _get_answer_fallback(self) -> Dict[str, Any]:
        """Get fallback answer response."""
        return {
            "success": True,
            "answer": "I'm sorry, but I'm unable to generate an answer at this time. Please try again later.",
            "sources": [],
            "source_count": 0,
            "total_results": 0,
            "fallback": True
        }
    
    async def execute_with_fallback(self, operation: str, service_func: callable, 
                                  fallback_func: callable = None, *args, **kwargs) -> Dict[str, Any]:
        """Execute operation with fallback."""
        try:
            # Check if service is available
            if not self.is_service_available(operation):
                logger.warning(f"Service {operation} is unavailable, using fallback")
                if fallback_func:
                    return await fallback_func(*args, **kwargs)
                else:
                    return self.get_fallback_response(operation, kwargs.get('query'))
            
            # Try to execute the operation
            start_time = time.time()
            result = await service_func(*args, **kwargs)
            response_time = time.time() - start_time
            
            # Record success
            self.update_service_health(operation, ServiceStatus.HEALTHY, response_time)
            
            return result
            
        except Exception as e:
            # Record failure
            self.update_service_health(operation, ServiceStatus.UNHEALTHY, 0, str(e))
            
            logger.error(f"Operation {operation} failed: {e}")
            
            # Try fallback
            if fallback_func:
                try:
                    return await fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback for {operation} also failed: {fallback_error}")
            
            return self.get_fallback_response(operation, kwargs.get('query'))
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        healthy_services = sum(1 for health in self.service_health.values() 
                             if health.status == ServiceStatus.HEALTHY)
        total_services = len(self.service_health)
        
        if healthy_services == total_services:
            overall_status = "healthy"
        elif healthy_services > total_services // 2:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return {
            "overall_status": overall_status,
            "healthy_services": healthy_services,
            "total_services": total_services,
            "services": {
                name: {
                    "status": health.status.value,
                    "last_check": health.last_check.isoformat(),
                    "error_count": health.error_count,
                    "last_error": health.last_error,
                    "response_time": health.response_time,
                    "available": self.is_service_available(name)
                }
                for name, health in self.service_health.items()
            }
        }


class SearchDegradationManager:
    """Specialized degradation manager for search operations."""
    
    def __init__(self):
        self.degradation_manager = GracefulDegradationManager()
        self.cached_results: Dict[str, Any] = {}
        self.simple_search_enabled = True
    
    async def search_with_degradation(self, search_func: callable, query: str, 
                                    limit: int = 10, offset: int = 0, **kwargs) -> Dict[str, Any]:
        """Perform search with graceful degradation."""
        
        # Try full search first
        try:
            if self.degradation_manager.is_service_available('search_system'):
                result = await search_func(query, limit, offset, **kwargs)
                
                if result and result.get('success'):
                    self.degradation_manager.update_service_health(
                        'search_system', ServiceStatus.HEALTHY
                    )
                    return result
        except Exception as e:
            logger.error(f"Full search failed: {e}")
            self.degradation_manager.update_service_health(
                'search_system', ServiceStatus.UNHEALTHY, 0, str(e)
            )
        
        # Try cached results
        cache_key = f"search:{query}:{limit}:{offset}"
        if cache_key in self.cached_results:
            logger.info(f"Using cached results for degraded search: {query}")
            cached_result = self.cached_results[cache_key]
            cached_result['metadata']['fallback_mode'] = True
            cached_result['metadata']['message'] = "Using cached results due to service degradation"
            return cached_result
        
        # Try simple text search fallback
        if self.simple_search_enabled:
            try:
                simple_result = await self._simple_text_search(query, limit, offset)
                if simple_result:
                    logger.info(f"Using simple text search fallback for: {query}")
                    return simple_result
            except Exception as e:
                logger.error(f"Simple search fallback failed: {e}")
        
        # Return empty results with helpful message
        return self.degradation_manager.get_fallback_response("search", query)
    
    async def _simple_text_search(self, query: str, limit: int, offset: int) -> Dict[str, Any]:
        """Simple text-based search fallback."""
        try:
            # This would implement a basic text search without AI or vector search
            # For now, return empty results
            return {
                "success": True,
                "results": [],
                "metadata": {
                    "query": query,
                    "total_results": 0,
                    "response_time": 0,
                    "has_answer": False,
                    "answer": "",
                    "fallback_mode": True,
                    "search_type": "simple_text",
                    "message": "Using simplified search due to service limitations"
                },
                "fallback": True
            }
        except Exception as e:
            logger.error(f"Simple text search failed: {e}")
            return None
    
    def cache_search_result(self, query: str, result: Dict[str, Any], limit: int, offset: int):
        """Cache search result for fallback use."""
        cache_key = f"search:{query}:{limit}:{offset}"
        self.cached_results[cache_key] = result
        
        # Limit cache size
        if len(self.cached_results) > 100:
            # Remove oldest entries
            oldest_key = next(iter(self.cached_results))
            del self.cached_results[oldest_key]
    
    def get_degradation_status(self) -> Dict[str, Any]:
        """Get degradation status."""
        system_status = self.degradation_manager.get_system_status()
        system_status['cached_results_count'] = len(self.cached_results)
        system_status['simple_search_enabled'] = self.simple_search_enabled
        return system_status


# Global degradation manager instances
degradation_manager = GracefulDegradationManager()
search_degradation_manager = SearchDegradationManager()


def get_degradation_manager() -> GracefulDegradationManager:
    """Get the global degradation manager."""
    return degradation_manager


def get_search_degradation_manager() -> SearchDegradationManager:
    """Get the global search degradation manager."""
    return search_degradation_manager

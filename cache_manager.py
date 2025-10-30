"""
Advanced caching strategy for the hybrid search API.
Implements multi-level caching with intelligent invalidation.
"""
import asyncio
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import weakref

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level enumeration."""
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"


class CacheStrategy(Enum):
    """Cache strategy enumeration."""
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int
    last_accessed: datetime
    tags: List[str]
    level: CacheLevel


class CacheManager:
    """Advanced cache manager with multiple strategies."""
    
    def __init__(self):
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.access_times: Dict[str, datetime] = {}
        self.max_memory_size = 1000  # Maximum entries in memory
        self.default_ttl = 3600  # 1 hour default TTL
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    async def _cleanup_expired(self):
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                now = datetime.utcnow()
                
                expired_keys = []
                for key, entry in self.memory_cache.items():
                    if entry.expires_at < now:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.memory_cache[key]
                    if key in self.access_times:
                        del self.access_times[key]
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters."""
        # Sort kwargs for consistent keys
        sorted_kwargs = sorted(kwargs.items())
        key_data = f"{prefix}:{json.dumps(sorted_kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _should_cache(self, query: str, result_count: int) -> Tuple[bool, int]:
        """Determine if query should be cached and TTL."""
        query_lower = query.lower()
        
        # Don't cache very short queries
        if len(query.strip()) < 3:
            return False, 0
        
        # Don't cache queries with zero results (might be content gaps)
        if result_count == 0:
            return False, 0
        
        # Cache popular queries longer
        popular_keywords = ['contact', 'about', 'services', 'team', 'careers']
        if any(keyword in query_lower for keyword in popular_keywords):
            return True, 7200  # 2 hours
        
        # Cache navigational queries longer
        navigational_keywords = ['login', 'account', 'dashboard', 'profile']
        if any(keyword in query_lower for keyword in navigational_keywords):
            return True, 10800  # 3 hours
        
        # Cache informational queries medium
        informational_keywords = ['how', 'what', 'why', 'when', 'where']
        if any(keyword in query_lower for keyword in informational_keywords):
            return True, 1800  # 30 minutes
        
        # Default caching
        return True, self.default_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            
            # Check if expired
            if entry.expires_at < datetime.utcnow():
                del self.memory_cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                return None
            
            # Update access metadata
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            self.access_times[key] = datetime.utcnow()
            
            logger.debug(f"Cache hit for key: {key}")
            return entry.value
        
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None, tags: List[str] = None) -> bool:
        """Set value in cache."""
        try:
            if ttl is None:
                ttl = self.default_ttl
            
            now = datetime.utcnow()
            expires_at = now + timedelta(seconds=ttl)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=expires_at,
                access_count=1,
                last_accessed=now,
                tags=tags or [],
                level=CacheLevel.MEMORY
            )
            
            # Evict if cache is full
            if len(self.memory_cache) >= self.max_memory_size:
                await self._evict_lru()
            
            self.memory_cache[key] = entry
            self.access_times[key] = now
            
            logger.debug(f"Cached value for key: {key}, TTL: {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def _evict_lru(self):
        """Evict least recently used entries."""
        if not self.access_times:
            return
        
        # Sort by access time (oldest first)
        sorted_times = sorted(self.access_times.items(), key=lambda x: x[1])
        
        # Remove oldest 10% of entries
        evict_count = max(1, len(sorted_times) // 10)
        
        for key, _ in sorted_times[:evict_count]:
            if key in self.memory_cache:
                del self.memory_cache[key]
            if key in self.access_times:
                del self.access_times[key]
        
        logger.debug(f"Evicted {evict_count} LRU cache entries")
    
    async def invalidate_by_tags(self, tags: List[str]):
        """Invalidate cache entries by tags."""
        invalidated = 0
        
        for key, entry in list(self.memory_cache.items()):
            if any(tag in entry.tags for tag in tags):
                del self.memory_cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                invalidated += 1
        
        logger.info(f"Invalidated {invalidated} cache entries by tags: {tags}")
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        invalidated = 0
        
        for key in list(self.memory_cache.keys()):
            if pattern in key:
                del self.memory_cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                invalidated += 1
        
        logger.info(f"Invalidated {invalidated} cache entries matching pattern: {pattern}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        
        # Calculate hit rate (simplified)
        total_entries = len(self.memory_cache)
        expired_entries = sum(1 for entry in self.memory_cache.values() 
                            if entry.expires_at < now)
        
        # Calculate average access count
        avg_access = (sum(entry.access_count for entry in self.memory_cache.values()) 
                     / total_entries) if total_entries > 0 else 0
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "max_size": self.max_memory_size,
            "utilization_percent": (total_entries / self.max_memory_size) * 100,
            "average_access_count": round(avg_access, 2),
            "memory_usage_mb": self._estimate_memory_usage(),
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        total_size = 0
        for entry in self.memory_cache.values():
            try:
                total_size += len(json.dumps(entry.value))
            except:
                total_size += 1000  # Estimate for non-serializable objects
        
        return round(total_size / (1024 * 1024), 2)
    
    async def clear(self):
        """Clear all cache entries."""
        self.memory_cache.clear()
        self.access_times.clear()
        logger.info("Cache cleared")
    
    async def close(self):
        """Close cache manager."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


class SearchCacheManager:
    """Specialized cache manager for search results."""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.query_cache_stats: Dict[str, int] = {}
    
    def _get_search_key(self, query: str, limit: int, offset: int, **kwargs) -> str:
        """Generate search-specific cache key."""
        return self.cache_manager._generate_key(
            "search",
            query=query,
            limit=limit,
            offset=offset,
            **kwargs
        )
    
    async def get_search_results(self, query: str, limit: int, offset: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Get cached search results."""
        key = self._get_search_key(query, limit, offset, **kwargs)
        return await self.cache_manager.get(key)
    
    async def set_search_results(self, query: str, results: Dict[str, Any], limit: int, offset: int, **kwargs) -> bool:
        """Cache search results."""
        key = self._get_search_key(query, limit, offset, **kwargs)
        
        # Determine caching strategy
        result_count = len(results.get('results', []))
        should_cache, ttl = self.cache_manager._should_cache(query, result_count)
        
        if not should_cache:
            logger.debug(f"Not caching query: {query} (result_count: {result_count})")
            return False
        
        # Add metadata to cached results
        cached_results = {
            **results,
            '_cached_at': datetime.utcnow().isoformat(),
            '_cache_ttl': ttl,
            '_query': query,
        }
        
        # Determine tags for invalidation
        tags = ['search_results']
        if 'filters' in kwargs:
            tags.append('filtered_search')
        
        return await self.cache_manager.set(key, cached_results, ttl, tags)
    
    async def invalidate_search_cache(self, query_pattern: str = None):
        """Invalidate search cache."""
        if query_pattern:
            await self.cache_manager.invalidate_pattern(f"search:{query_pattern}")
        else:
            await self.cache_manager.invalidate_by_tags(['search_results'])
    
    def track_query_frequency(self, query: str):
        """Track query frequency for cache optimization."""
        query_lower = query.lower()
        self.query_cache_stats[query_lower] = self.query_cache_stats.get(query_lower, 0) + 1
    
    def get_popular_queries(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most popular queries."""
        return sorted(
            self.query_cache_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search cache statistics."""
        cache_stats = self.cache_manager.get_stats()
        cache_stats['popular_queries'] = self.get_popular_queries(5)
        cache_stats['total_unique_queries'] = len(self.query_cache_stats)
        return cache_stats


# Global cache manager instances
cache_manager = CacheManager()
search_cache_manager = SearchCacheManager()


async def cleanup_cache():
    """Cleanup function for graceful shutdown."""
    await cache_manager.close()
    await search_cache_manager.cache_manager.close()


def get_cache_manager() -> CacheManager:
    """Get the global cache manager."""
    return cache_manager


def get_search_cache_manager() -> SearchCacheManager:
    """Get the global search cache manager."""
    return search_cache_manager




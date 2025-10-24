"""
Connection Pool Manager for Hybrid Search API.
Manages HTTP connections, database connections, and other resources efficiently.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
import httpx
from contextlib import asynccontextmanager
import weakref

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """Manages connection pools for various services."""
    
    def __init__(self):
        self._pools: Dict[str, Any] = {}
        self._cleanup_tasks: Dict[str, asyncio.Task] = {}
        self._refs = weakref.WeakValueDictionary()
    
    async def get_http_client(self, name: str, **kwargs) -> httpx.AsyncClient:
        """Get or create an HTTP client with connection pooling."""
        if name not in self._pools:
            # Default connection limits
            limits = httpx.Limits(
                max_keepalive_connections=kwargs.get('max_keepalive', 20),
                max_connections=kwargs.get('max_connections', 100),
                keepalive_expiry=kwargs.get('keepalive_expiry', 30.0)
            )
            
            self._pools[name] = httpx.AsyncClient(
                limits=limits,
                timeout=kwargs.get('timeout', 30.0),
                headers=kwargs.get('headers', {}),
                http2=kwargs.get('http2', True),
                **kwargs
            )
            
            # Set up cleanup task
            self._cleanup_tasks[name] = asyncio.create_task(
                self._cleanup_client(name)
            )
            
            logger.info(f"Created HTTP client pool: {name}")
        
        return self._pools[name]
    
    async def _cleanup_client(self, name: str):
        """Cleanup client after inactivity."""
        try:
            # Wait for 5 minutes of inactivity
            await asyncio.sleep(300)
            
            if name in self._pools:
                client = self._pools[name]
                await client.aclose()
                del self._pools[name]
                logger.info(f"Cleaned up HTTP client pool: {name}")
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error cleaning up client {name}: {e}")
    
    @asynccontextmanager
    async def get_wordpress_client(self, base_url: str, auth: Optional[tuple] = None):
        """Get WordPress client with proper connection management."""
        client_name = f"wordpress_{hash(base_url)}"
        
        client = await self.get_http_client(
            client_name,
            auth=auth,
            base_url=base_url,
            timeout=30.0,
            max_keepalive=20,
            max_connections=50,
            headers={"User-Agent": "HybridSearchBot/1.0"}
        )
        
        try:
            yield client
        finally:
            # Don't close here - let the pool manager handle it
            pass
    
    @asynccontextmanager
    async def get_cerebras_client(self, api_key: str, base_url: str):
        """Get Cerebras API client with connection pooling."""
        client_name = f"cerebras_{hash(api_key)}"
        
        client = await self.get_http_client(
            client_name,
            base_url=base_url,
            timeout=60.0,  # Longer timeout for LLM requests
            max_keepalive=10,
            max_connections=20,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "HybridSearchBot/1.0"
            }
        )
        
        try:
            yield client
        finally:
            pass
    
    async def close_all(self):
        """Close all connection pools."""
        logger.info("Closing all connection pools...")
        
        # Cancel cleanup tasks
        for task in self._cleanup_tasks.values():
            task.cancel()
        
        # Close all clients
        for name, client in self._pools.items():
            try:
                await client.aclose()
                logger.info(f"Closed client pool: {name}")
            except Exception as e:
                logger.error(f"Error closing client {name}: {e}")
        
        self._pools.clear()
        self._cleanup_tasks.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        stats = {
            "active_pools": len(self._pools),
            "pools": {}
        }
        
        for name, client in self._pools.items():
            try:
                stats["pools"][name] = {
                    "is_closed": client.is_closed,
                    "limits": {
                        "max_connections": client.limits.max_connections,
                        "max_keepalive": client.limits.max_keepalive_connections,
                    }
                }
            except Exception as e:
                stats["pools"][name] = {"error": str(e)}
        
        return stats


# Global connection pool manager instance
connection_manager = ConnectionPoolManager()


async def cleanup_connections():
    """Cleanup function for graceful shutdown."""
    await connection_manager.close_all()


def get_connection_manager() -> ConnectionPoolManager:
    """Get the global connection pool manager."""
    return connection_manager


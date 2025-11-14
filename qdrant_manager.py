"""
Qdrant vector database configuration and management.

This module provides a high-level interface for interacting with Qdrant,
including collection management, document indexing, and hybrid search operations.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, 
    MatchValue, SearchRequest, ScoredPoint
)
from qdrant_client.http import models
import numpy as np
from numpy.typing import NDArray
from config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    """
    Manages Qdrant vector database operations for hybrid search.
    
    This class provides methods for:
    - Creating and managing collections
    - Indexing documents with dense and sparse vectors
    - Performing hybrid search queries
    - Managing document lifecycle
    
    Attributes:
        client: QdrantClient instance for database operations
        collection_name: Name of the collection being managed
        embedding_dimension: Dimension of dense vectors
    """
    
    def __init__(self) -> None:
        """Initialize Qdrant client and configuration."""
        # Add timeout settings to prevent hanging
        self.client: QdrantClient = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=10.0,  # Reduced to 10 seconds for faster failure detection
            prefer_grpc=False  # Use HTTP instead of gRPC for better timeout handling
        )
        self.collection_name: str = settings.qdrant_collection_name
        self.embedding_dimension: int = settings.embedding_dimension
        self._is_available: Optional[bool] = None  # Cache availability status
        self._last_health_check: float = 0.0  # Track last health check time
        self._health_check_interval: float = 60.0  # Check health every 60 seconds
    
    def check_health(self) -> bool:
        """
        Check if Qdrant is available and responsive.
        Uses cached result if checked recently.
        
        Returns:
            True if Qdrant is available, False otherwise
        """
        import time
        current_time = time.time()
        
        # Use cached result if checked recently
        if self._is_available is not None and (current_time - self._last_health_check) < self._health_check_interval:
            return self._is_available
        
        # Perform health check
        try:
            # Try a simple operation with short timeout
            self.client.get_collections()
            self._is_available = True
            self._last_health_check = current_time
            logger.debug(f"Qdrant health check passed: {settings.qdrant_url}")
            return True
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "unknown error"
            logger.warning(f"Qdrant health check failed ({error_type}): {error_msg}")
            self._is_available = False
            self._last_health_check = current_time
            return False
    
    def create_collection(self) -> bool:
        """Create the collection if it doesn't exist."""
        # Check health first
        if not self.check_health():
            logger.warning(f"Qdrant is unavailable at {settings.qdrant_url}, cannot create collection")
            return False
        
        import time
        max_retries = 2  # Reduced retries since we check health first
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Check if collection exists with timeout handling
                try:
                    collections = self.client.get_collections()
                    collection_names = [col.name for col in collections.collections]
                    
                    if self.collection_name in collection_names:
                        logger.info(f"Collection '{self.collection_name}' already exists")
                        return True
                except Exception as check_e:
                    error_msg = str(check_e) if str(check_e) else f"{type(check_e).__name__} (no message)"
                    if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                        logger.error(f"Qdrant timeout while checking collection existence: {error_msg}")
                        self._is_available = False
                        return False
                    logger.warning(f"Error checking collection existence (attempt {attempt + 1}/{max_retries}): {error_msg}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise
                
                # Create collection with simple vector configuration
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                
                logger.info(f"Created collection '{self.collection_name}'")
                return True
                
            except Exception as e:
                error_msg = str(e) if str(e) else f"{type(e).__name__} (no message)"
                error_type = type(e).__name__
                
                # Mark as unavailable if it's a timeout
                if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                    logger.error(f"Qdrant timeout while creating collection: {error_msg}")
                    self._is_available = False
                    return False
                
                logger.error(f"Error creating collection (attempt {attempt + 1}/{max_retries}): {error_type}: {error_msg}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to create collection after {max_retries} attempts")
                    return False
        
        return False
    
    def delete_collection(self) -> bool:
        """Delete the collection."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection '{self.collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """Clear all points from the collection without deleting it."""
        try:
            # Delete all points using scroll and delete
            limit = 100
            offset = None
            deleted_count = 0
            
            while True:
                # Scroll to get point IDs
                scroll_result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=limit,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False
                )
                
                points = scroll_result[0]
                if not points:
                    break
                
                # Extract point IDs
                point_ids = [point.id for point in points]
                
                # Delete these points
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
                
                deleted_count += len(point_ids)
                logger.info(f"Deleted {deleted_count} points so far...")
                
                # Update offset for next iteration
                offset = scroll_result[1]
                if not offset:
                    break
            
            logger.info(f"Cleared {deleted_count} points from collection '{self.collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False
    
    def upsert_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Insert or update documents in the collection."""
        # Check health first
        if not self.check_health():
            logger.warning(f"Qdrant is unavailable, skipping document upsert")
            return False
        
        try:
            points = []
            
            for doc in documents:
                # Create point ID from document ID (must be integer or UUID)
                # Convert doc['id'] to integer using hash for consistent mapping
                try:
                    # If doc['id'] is already a number, use it
                    if isinstance(doc['id'], (int, float)):
                        point_id = int(doc['id']) % (10 ** 18)  # Keep in valid range
                    else:
                        # Convert string ID to integer using hash
                        point_id = abs(hash(str(doc['id']))) % (10 ** 18)
                except:
                    # Fallback: use simple hash
                    point_id = abs(hash(str(doc['id']))) % (10 ** 18)
                
                # Prepare dense vector (embedding)
                dense_vector = doc.get('embedding', [0.0] * self.embedding_dimension)
                
                # Prepare sparse vector (BM25-like weights)
                sparse_vector = doc.get('sparse_vector', {})
                
                # Create payload with document metadata
                payload = {
                    "id": doc["id"],
                    "title": doc["title"],
                    "slug": doc["slug"],
                    "type": doc["type"],
                    "url": doc["url"],
                    "date": doc["date"],
                    "modified": doc["modified"],
                    "author": doc["author"],
                    "categories": doc["categories"],
                    "tags": doc["tags"],
                    "excerpt": doc["excerpt"],
                    "content": doc["content"],
                    "word_count": doc["word_count"],
                    "featured_image": doc.get("featured_image", ""),
                    "featured_media": doc.get("featured_media", 0),
                    "text": f"{doc['title']} {doc['content']}"  # Combined text for search
                }
                
                # Create point structure
                point = PointStruct(
                    id=point_id,
                    vector=dense_vector,
                    payload=payload
                )
                
                points.append(point)
            
            # Upsert points in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                logger.info(f"Upserted batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")
            
            logger.info(f"Successfully upserted {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Error upserting documents: {e}")
            return False
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a single document from the collection by ID."""
        # Check health first
        if not self.check_health():
            logger.warning(f"Qdrant is unavailable, skipping document deletion")
            return False
        
        try:
            # Convert document ID to point ID (same logic as upsert)
            try:
                if isinstance(document_id, (int, float)):
                    point_id = int(document_id) % (10 ** 18)
                else:
                    point_id = abs(hash(str(document_id))) % (10 ** 18)
            except:
                point_id = abs(hash(str(document_id))) % (10 ** 18)
            
            # Delete the point
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
            
            logger.info(f"Successfully deleted document {document_id} (point ID: {point_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    def hybrid_search(
        self, 
        query: str, 
        dense_vector: List[float],
        sparse_vector: Dict[int, float],
        limit: int = 10,
        alpha: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining dense and sparse vectors.
        
        Args:
            query: Search query text
            dense_vector: Dense embedding vector
            sparse_vector: Sparse BM25-like vector
            limit: Maximum number of results
            alpha: Weight for dense vs sparse (0.0 = sparse only, 1.0 = dense only)
        """
        # Check health first
        if not self.check_health():
            logger.debug(f"Qdrant is unavailable, returning empty results for hybrid search")
            return []
        
        try:
            # Perform dense search
            dense_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=dense_vector,
                limit=limit * 2,  # Get more results for hybrid scoring
                with_payload=True,
                with_vectors=False
            )
            
            # For now, return dense results with hybrid scoring
            # In a full implementation, you would also perform sparse search
            # and combine the results using alpha weighting
            
            results = []
            for result in dense_results:
                # Calculate hybrid score (currently just dense score)
                hybrid_score = result.score * alpha
                
                result_data = {
                    "id": result.payload["id"],
                    "title": result.payload["title"],
                    "slug": result.payload["slug"],
                    "type": result.payload["type"],
                    "url": result.payload["url"],
                    "date": result.payload["date"],
                    "modified": result.payload["modified"],
                    "author": result.payload["author"],
                    "categories": result.payload["categories"],
                    "tags": result.payload["tags"],
                    "excerpt": result.payload["excerpt"],
                    "content": result.payload["content"],
                    "word_count": result.payload["word_count"],
                    "score": hybrid_score,
                    "relevance": self._calculate_relevance(hybrid_score, alpha)
                }
                results.append(result_data)
            
            # Sort by hybrid score and limit results
            results.sort(key=lambda x: x['score'], reverse=True)
            results = results[:limit]
            
            logger.info(f"Hybrid search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error performing hybrid search: {e}")
            return []
    
    def _calculate_relevance(self, score: float, alpha: float) -> str:
        """Calculate relevance level based on score."""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "very_low"
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        # Check health first
        if not self.check_health():
            logger.warning(f"Qdrant is unavailable at {settings.qdrant_url}, skipping collection info")
            return {}
        
        import time
        max_retries = 1  # Reduced retries since we check health first
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                collection_info = self.client.get_collection(self.collection_name)
                # Access vectors config properly - it's either a dict or a VectorParams object
                try:
                    if hasattr(collection_info.config.params.vectors, 'size'):
                        # It's a VectorParams object
                        vector_size = collection_info.config.params.vectors.size
                    elif isinstance(collection_info.config.params.vectors, dict):
                        # It's a dict with "dense" key
                        vector_size = collection_info.config.params.vectors.get("dense", {}).get("size", 0)
                    else:
                        vector_size = 0
                except:
                    vector_size = 0
                
                # Get vector counts - handle different Qdrant API versions
                vectors_count = 0
                indexed_vectors_count = 0
                
                # Try to get vectors_count - it might be an attribute or property
                try:
                    if hasattr(collection_info, 'vectors_count'):
                        vectors_count = collection_info.vectors_count or 0
                    elif hasattr(collection_info, 'vectors') and hasattr(collection_info.vectors, 'count'):
                        vectors_count = collection_info.vectors.count or 0
                except Exception as e:
                    logger.debug(f"Could not get vectors_count: {e}")
                
                # Try to get indexed_vectors_count
                try:
                    if hasattr(collection_info, 'indexed_vectors_count'):
                        indexed_vectors_count = collection_info.indexed_vectors_count or 0
                    elif hasattr(collection_info, 'vectors') and hasattr(collection_info.vectors, 'indexed_count'):
                        indexed_vectors_count = collection_info.vectors.indexed_count or 0
                except Exception as e:
                    logger.debug(f"Could not get indexed_vectors_count: {e}")
                
                # Get points_count
                points_count = 0
                try:
                    if hasattr(collection_info, 'points_count'):
                        points_count = collection_info.points_count or 0
                except Exception as e:
                    logger.debug(f"Could not get points_count: {e}")
                
                # Log what we're getting for debugging
                logger.debug(f"Qdrant collection info - points_count: {points_count}, vectors_count: {vectors_count}, indexed_vectors_count: {indexed_vectors_count}")
                
                return {
                    "name": self.collection_name,
                    "vector_size": vector_size,
                    "vectors_count": vectors_count,
                    "indexed_vectors_count": indexed_vectors_count,
                    "points_count": points_count,
                    "segments_count": getattr(collection_info, 'segments_count', 0),
                    "status": getattr(collection_info, 'status', 'unknown')
                }
            except Exception as e:
                error_msg = str(e) if str(e) else f"{type(e).__name__} (no message)"
                error_type = type(e).__name__
                
                # Mark as unavailable if it's a timeout or connection error
                if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower() or 'connection' in error_msg.lower():
                    logger.error(f"Qdrant connection failed ({error_type}): {error_msg}")
                    self._is_available = False
                    return {}
                
                logger.warning(f"Error getting collection info (attempt {attempt + 1}/{max_retries}): {error_type}: {error_msg}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    # Final attempt failed, try auto-create only if it's not a timeout
                    if 'timeout' not in error_msg.lower() and 'timed out' not in error_msg.lower():
                        logger.info(f"Collection '{self.collection_name}' doesn't exist, attempting to create it...")
                        try:
                            if self.create_collection():
                                logger.info(f"✅ Successfully created collection '{self.collection_name}'")
                                # Try getting info again
                                try:
                                    collection_info = self.client.get_collection(self.collection_name)
                                    # Use same logic as above for vector_size
                                    try:
                                        if hasattr(collection_info.config.params.vectors, 'size'):
                                            vector_size = collection_info.config.params.vectors.size
                                        elif isinstance(collection_info.config.params.vectors, dict):
                                            vector_size = collection_info.config.params.vectors.get("dense", {}).get("size", 0)
                                        else:
                                            vector_size = 0
                                    except:
                                        vector_size = 0
                                    
                                    # Get vector counts - handle different Qdrant API versions
                                    vectors_count = 0
                                    indexed_vectors_count = 0
                                    
                                    try:
                                        if hasattr(collection_info, 'vectors_count'):
                                            vectors_count = collection_info.vectors_count or 0
                                        elif hasattr(collection_info, 'vectors') and hasattr(collection_info.vectors, 'count'):
                                            vectors_count = collection_info.vectors.count or 0
                                    except Exception as e:
                                        logger.debug(f"Could not get vectors_count: {e}")
                                    
                                    try:
                                        if hasattr(collection_info, 'indexed_vectors_count'):
                                            indexed_vectors_count = collection_info.indexed_vectors_count or 0
                                        elif hasattr(collection_info, 'vectors') and hasattr(collection_info.vectors, 'indexed_count'):
                                            indexed_vectors_count = collection_info.vectors.indexed_count or 0
                                    except Exception as e:
                                        logger.debug(f"Could not get indexed_vectors_count: {e}")
                                    
                                    points_count = 0
                                    try:
                                        if hasattr(collection_info, 'points_count'):
                                            points_count = collection_info.points_count or 0
                                    except Exception as e:
                                        logger.debug(f"Could not get points_count: {e}")
                                    
                                    return {
                                        "name": self.collection_name,
                                        "vector_size": vector_size,
                                        "vectors_count": vectors_count,
                                        "indexed_vectors_count": indexed_vectors_count,
                                        "points_count": points_count,
                                        "segments_count": getattr(collection_info, 'segments_count', 0),
                                        "status": getattr(collection_info, 'status', 'unknown')
                                    }
                                except Exception as retry_e:
                                    logger.error(f"Error getting collection info after creation: {retry_e}")
                                    return {}
                            else:
                                logger.error(f"Failed to create collection '{self.collection_name}'")
                                return {}
                        except Exception as create_e:
                            logger.error(f"Error during auto-creation: {create_e}")
                            return {}
                    else:
                        logger.error(f"Qdrant timeout - cannot get collection info")
                        return {}
        
        return {}
    
    def search_by_filters(
        self, 
        filters: Dict[str, Any], 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search documents using filters."""
        try:
            # Build filter conditions
            conditions = []
            
            if "type" in filters:
                conditions.append(
                    FieldCondition(
                        key="type",
                        match=MatchValue(value=filters["type"])
                    )
                )
            
            if "author" in filters:
                conditions.append(
                    FieldCondition(
                        key="author",
                        match=MatchValue(value=filters["author"])
                    )
                )
            
            if "categories" in filters:
                conditions.append(
                    FieldCondition(
                        key="categories",
                        match=MatchValue(value=filters["categories"])
                    )
                )
            
            # Perform filtered search
            search_results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(must=conditions) if conditions else None,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            results = []
            for point in search_results[0]:  # scroll returns (points, next_page_offset)
                result_data = {
                    "id": point.payload["id"],
                    "title": point.payload["title"],
                    "slug": point.payload["slug"],
                    "type": point.payload["type"],
                    "url": point.payload["url"],
                    "date": point.payload["date"],
                    "modified": point.payload["modified"],
                    "author": point.payload["author"],
                    "categories": point.payload["categories"],
                    "tags": point.payload["tags"],
                    "excerpt": point.payload["excerpt"],
                    "content": point.payload["content"],
                    "word_count": point.payload["word_count"]
                }
                results.append(result_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing filtered search: {e}")
            return []
    
    def close(self):
        """Close the Qdrant client."""
        # Qdrant client doesn't have a close method, but we can clean up
        pass

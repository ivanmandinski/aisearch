"""
Qdrant vector database configuration and management.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, 
    MatchValue, SearchRequest, Query
)
from qdrant_client.http import models
import numpy as np
from config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    """Manages Qdrant vector database operations for hybrid search."""
    
    def __init__(self):
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        self.collection_name = settings.qdrant_collection_name
        self.embedding_dimension = settings.embedding_dimension
    
    def create_collection(self) -> bool:
        """Create the collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name in collection_names:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return True
            
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
            logger.error(f"Error creating collection: {e}")
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
    
    def upsert_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Insert or update documents in the collection."""
        try:
            points = []
            
            for doc in documents:
                # Create point ID from document ID
                point_id = f"doc_{doc['id']}"
                
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
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": collection_info.config.params.vectors["dense"].size,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
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

"""
Simplified hybrid search implementation without complex LlamaIndex dependencies.
"""
import logging
from typing import List, Dict, Any, Optional
import httpx
import asyncio
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
from config import settings

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    from qdrant_manager import QdrantManager
    QDRANT_AVAILABLE = True
except ImportError as e:
    logging.error(f"Failed to import QdrantManager: {e}")
    QdrantManager = None
    QDRANT_AVAILABLE = False

try:
    from cerebras_llm import CerebrasLLM
    CEREBRAS_AVAILABLE = True
except ImportError as e:
    logging.error(f"Failed to import CerebrasLLM: {e}")
    CerebrasLLM = None
    CEREBRAS_AVAILABLE = False


class SimpleHybridSearch:
    """Simplified hybrid search implementation."""
    
    def __init__(self):
        # Initialize Qdrant if available
        if QDRANT_AVAILABLE and QdrantManager is not None:
            try:
                logger.info("Initializing QdrantManager...")
                self.qdrant_manager = QdrantManager()
                logger.info("QdrantManager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize QdrantManager: {e}")
                self.qdrant_manager = None
        else:
            logger.warning("Qdrant not available - using fallback search only")
            self.qdrant_manager = None
        
        # Initialize Cerebras LLM if available
        if CEREBRAS_AVAILABLE and CerebrasLLM is not None:
            try:
                logger.info("Initializing CerebrasLLM...")
                self.llm_client = CerebrasLLM()
                logger.info("CerebrasLLM initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize CerebrasLLM: {e}")
                self.llm_client = None
        else:
            logger.warning("Cerebras LLM not available - AI answers disabled")
            self.llm_client = None
        
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.tfidf_matrix = None
        self.documents = []
        self.document_texts = []
        
        # Initialize with sample data for testing (fallback)
        self._initialize_with_sample_data()
    
    def _initialize_with_sample_data(self):
        """Initialize with sample data for testing."""
        try:
            sample_docs = [
                {
                    'id': 'sample1',
                    'title': 'Energy Audit Services',
                    'slug': 'energy-audit',
                    'type': 'post',
                    'url': 'https://www.scsengineers.com/energy-audit/',
                    'date': '2024-01-01',
                    'modified': '2024-01-01',
                    'author': 'SCS Engineers',
                    'categories': [],
                    'tags': [],
                    'excerpt': 'Professional energy audit services for industrial facilities.',
                    'content': 'SCS Engineers provides comprehensive energy audit services to help industrial facilities reduce energy costs and improve efficiency. Our certified energy auditors use advanced tools and techniques to identify energy-saving opportunities.',
                    'word_count': 25
                },
                {
                    'id': 'sample2',
                    'title': 'Environmental Consulting',
                    'slug': 'environmental-consulting',
                    'type': 'post',
                    'url': 'https://www.scsengineers.com/environmental-consulting/',
                    'date': '2024-01-02',
                    'modified': '2024-01-02',
                    'author': 'SCS Engineers',
                    'categories': [],
                    'tags': [],
                    'excerpt': 'Expert environmental consulting services.',
                    'content': 'SCS Engineers offers environmental consulting services including environmental impact assessments, remediation planning, and regulatory compliance assistance.',
                    'word_count': 20
                },
                {
                    'id': 'sample3',
                    'title': 'Waste Management Solutions',
                    'slug': 'waste-management',
                    'type': 'post',
                    'url': 'https://www.scsengineers.com/waste-management/',
                    'date': '2024-01-03',
                    'modified': '2024-01-03',
                    'author': 'SCS Engineers',
                    'categories': [],
                    'tags': [],
                    'excerpt': 'Comprehensive waste management solutions.',
                    'content': 'SCS Engineers provides innovative waste management solutions for industrial and municipal clients. Our services include waste characterization, treatment design, and regulatory compliance.',
                    'word_count': 22
                }
            ]
            
            # Prepare documents for TF-IDF
            document_texts = []
            for doc in sample_docs:
                combined_text = f"{doc['title']} {doc['content']}"
                document_texts.append(combined_text)
            
            # Fit TF-IDF
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(document_texts)
            self.document_texts = document_texts
            self.documents = sample_docs
            
            logger.info(f"Initialized with {len(sample_docs)} sample documents")
            
        except Exception as e:
            logger.error(f"Error initializing sample data: {e}")
    
    async def index_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Index documents for search."""
        try:
            logger.info(f"Indexing {len(documents)} documents...")
            
            if not documents:
                logger.warning("No documents to index")
                return False
            
            # Prepare documents for indexing
            processed_docs = []
            document_texts = []
            
            for doc in documents:
                try:
                    # Create combined text for embedding
                    combined_text = f"{doc['title']} {doc['content']}"
                    document_texts.append(combined_text)
                    
                    # Skip embedding generation for now - use zero vector
                    embedding = [0.0] * 384
                    
                    # Prepare sparse vector
                    processed_doc = {
                        'id': doc['id'],
                        'title': doc['title'],
                        'slug': doc['slug'],
                        'type': doc['type'],
                        'url': doc['url'],
                        'date': doc['date'],
                        'modified': doc['modified'],
                        'author': doc['author'],
                        'categories': doc['categories'],
                        'tags': doc['tags'],
                        'excerpt': doc['excerpt'],
                        'content': doc['content'],
                        'word_count': doc['word_count'],
                        'embedding': embedding,
                        'sparse_vector': {}  # Will be filled after TF-IDF fitting
                    }
                    processed_docs.append(processed_doc)
                    
                except Exception as e:
                    logger.error(f"Error processing document {doc.get('id', 'unknown')}: {e}")
                    continue
            
            if not processed_docs:
                logger.error("No documents were successfully processed")
                return False
            
            # Fit TF-IDF on all documents
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(document_texts)
            self.document_texts = document_texts
            
            # Add sparse vectors to documents
            for i, doc in enumerate(processed_docs):
                sparse_vector = self._get_sparse_vector(document_texts[i])
                doc['sparse_vector'] = sparse_vector
            
            # Store documents in memory for TF-IDF search
            self.documents = processed_docs
            
            # Skip Qdrant indexing for now - use in-memory search only
            logger.info(f"Successfully indexed {len(processed_docs)} documents in memory")
            return True
                
        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
            return False
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform TF-IDF only search (fallback when embeddings fail)."""
        try:
            # If we have TF-IDF fitted, use it for search
            if self.tfidf_matrix is not None and len(self.documents) > 0:
                logger.info("Using TF-IDF search as fallback")
                return self._tfidf_search(query, limit)
            
            # Fallback to simple text search
            logger.info("Using simple text search as fallback")
            return self._simple_text_search(query, limit)
            
        except Exception as e:
            logger.error(f"Error performing search: {e}")
            return []
    
    async def search_with_answer(self, query: str, limit: int = 5, custom_instructions: str = "") -> Dict[str, Any]:
        """Search and generate AI answer."""
        try:
            # Get search results
            results = await self.search(query, limit)
            
            if not results:
                return {
                    'query': query,
                    'answer': "I couldn't find any relevant information to answer your question.",
                    'sources': [],
                    'source_count': 0
                }
            
            # Generate answer using LLM with custom instructions
            if self.llm_client:
                try:
                    answer = self.llm_client.generate_answer(query, results, custom_instructions)
                except Exception as e:
                    logger.error(f"LLM answer generation failed: {e}")
                    answer = "I found relevant results but couldn't generate a summary at this time."
            else:
                logger.warning("LLM client not available, skipping answer generation")
                answer = "LLM service is currently unavailable. Please review the search results below."
            
            return {
                'query': query,
                'answer': answer,
                'sources': results,
                'source_count': len(results)
            }
            
        except Exception as e:
            logger.error(f"Error in search with answer: {e}")
            return {
                'query': query,
                'answer': "I encountered an error while generating an answer.",
                'sources': [],
                'source_count': 0
            }
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using simple hash-based embedding."""
        try:
            # Create a simple hash-based embedding for demo purposes
            # This is not as good as real embeddings but works for testing
            import hashlib
            import struct
            
            # Create a hash of the text
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Convert hash to 384-dimensional vector
            embedding = []
            for i in range(0, len(text_hash), 2):
                # Take pairs of hex characters and convert to float
                hex_pair = text_hash[i:i+2]
                value = int(hex_pair, 16) / 255.0  # Normalize to 0-1
                embedding.append(value)
            
            # Pad or truncate to exactly 384 dimensions
            while len(embedding) < 384:
                embedding.append(0.0)
            embedding = embedding[:384]
            
            return embedding
                
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 384
    
    def _get_sparse_vector(self, text: str) -> Dict[int, float]:
        """Get sparse vector using TF-IDF."""
        try:
            if self.tfidf_matrix is None:
                return {}
            
            # Transform text using fitted TF-IDF
            text_vector = self.tfidf_vectorizer.transform([text])
            
            # Convert to dictionary format
            sparse_vector = {}
            for idx, value in zip(text_vector.indices, text_vector.data):
                sparse_vector[int(idx)] = float(value)
            
            return sparse_vector
            
        except Exception as e:
            logger.error(f"Error getting sparse vector: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search statistics."""
        try:
            collection_info = self.qdrant_manager.get_collection_info()
            return {
                'collection_name': self.qdrant_manager.collection_name,
                'total_documents': collection_info.get('points_count', 0),
                'indexed_vectors': collection_info.get('indexed_vectors_count', 0),
                'status': collection_info.get('status', 'unknown'),
                'tfidf_fitted': self.tfidf_matrix is not None,
                'document_count': len(self.document_texts)
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def _tfidf_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Perform TF-IDF based search."""
        try:
            # Transform query using fitted TF-IDF
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Calculate cosine similarity with all documents
            similarities = []
            for i, doc_vector in enumerate(self.tfidf_matrix):
                # Calculate cosine similarity
                similarity = (query_vector * doc_vector.T).toarray()[0][0]
                similarities.append((i, similarity))
            
            # Sort by similarity and get top results
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for i, (doc_idx, score) in enumerate(similarities[:limit]):
                if score > 0:  # Only include results with positive similarity
                    doc = self.documents[doc_idx]
                    result = {
                        'id': doc['id'],
                        'title': doc['title'],
                        'url': doc['url'],
                        'excerpt': doc['excerpt'],
                        'score': float(score),
                        'relevance': 'high' if score > 0.1 else 'medium' if score > 0.05 else 'low'
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in TF-IDF search: {e}")
            return []
    
    def _simple_text_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Perform simple text-based search."""
        try:
            query_lower = query.lower()
            results = []
            
            for doc in self.documents:
                # Simple text matching
                title_score = query_lower in doc['title'].lower()
                content_score = query_lower in doc['content'].lower()
                excerpt_score = query_lower in doc['excerpt'].lower()
                
                # Calculate simple score
                score = 0
                if title_score:
                    score += 3
                if excerpt_score:
                    score += 2
                if content_score:
                    score += 1
                
                if score > 0:
                    result = {
                        'id': doc['id'],
                        'title': doc['title'],
                        'url': doc['url'],
                        'excerpt': doc['excerpt'],
                        'score': float(score),
                        'relevance': 'high' if score >= 3 else 'medium' if score >= 2 else 'low'
                    }
                    results.append(result)
            
            # Sort by score and limit results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error in simple text search: {e}")
            return []

    def close(self):
        """Close the search system."""
        if self.qdrant_manager:
            self.qdrant_manager.close()

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

# Try to import Sentence Transformers for real embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("Sentence Transformers available for semantic embeddings")
except ImportError as e:
    logging.warning(f"Sentence Transformers not available, will use fallback: {e}")
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class SimpleHybridSearch:
    """Simplified hybrid search implementation."""
    
    def __init__(self):
        # Initialize Sentence Transformers for real semantic embeddings
        if SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer is not None:
            try:
                logger.info("Initializing Sentence Transformer embedding model...")
                # Use lightweight, fast model (80MB, 500+ sentences/sec)
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Sentence Transformer model loaded successfully (all-MiniLM-L6-v2)")
            except Exception as e:
                logger.error(f"Failed to initialize embedding model: {e}")
                self.embedding_model = None
        else:
            logger.warning("Sentence Transformers not available - using hash-based fallback")
            self.embedding_model = None
        
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
        """Index documents for search with automatic chunking for long content."""
        try:
            logger.info(f"Indexing {len(documents)} documents...")
            
            if not documents:
                logger.warning("No documents to index")
                return False
            
            # Chunk long documents
            from content_chunker import ContentChunker
            chunker = ContentChunker(chunk_size=1000, overlap=200)
            chunked_documents = chunker.chunk_documents(documents)
            
            logger.info(f"After chunking: {len(chunked_documents)} total documents/chunks")
            
            # Prepare documents for indexing
            processed_docs = []
            document_texts = []
            
            for doc in chunked_documents:
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
                        'featured_image': doc.get('featured_image', ''),
                        'featured_media': doc.get('featured_media', 0),
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
    
    async def search(
        self, 
        query: str, 
        limit: int = 10,
        offset: int = 0,
        enable_ai_reranking: bool = True,
        ai_weight: float = 0.7,
        ai_reranking_instructions: str = "",
        enable_query_expansion: bool = True
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Perform search with optional AI reranking and query expansion.
        
        Args:
            query: Search query
            limit: Number of results to return
            offset: Number of results to skip (for pagination)
            enable_ai_reranking: Whether to use AI reranking
            ai_weight: Weight for AI score (0-1), higher = more AI influence
            ai_reranking_instructions: Custom instructions for AI reranking
            enable_query_expansion: Whether to expand query with synonyms
            
        Returns:
            (results, metadata) tuple
        """
        try:
            # Validate and sanitize pagination parameters
            if offset < 0:
                offset = 0
            if limit < 1:
                limit = 10
            if limit > 100:  # Add reasonable limit
                limit = 100
            
            logger.info(f"Search request: query='{query}', offset={offset}, limit={limit}")
            
            # Step 0: Query expansion (if enabled)
            search_queries = [query]
            if enable_query_expansion:
                try:
                    from query_expander import QueryExpander
                    expander = QueryExpander(llm_client=self.llm_client)
                    search_queries = expander.expand_query(query, max_expansions=3)
                    logger.info(f"Query expanded to: {search_queries}")
                except Exception as e:
                    logger.warning(f"Query expansion failed: {e}, using original query only")
            
            # Step 1: Get candidates using TF-IDF with proper pagination
            # For pagination to work correctly, we need to get a larger set of results
            # and then apply offset/limit consistently
            
            # Calculate how many results we need to get to ensure we have enough for pagination
            initial_limit = min(limit * 3, 200) if enable_ai_reranking else limit
            search_limit = max(initial_limit, offset + limit + 50)  # Get extra to ensure we have enough
            
            # Search with all expanded queries and combine results
            all_candidates = []
            seen_ids = set()
            
            for search_query in search_queries:
                # If we have TF-IDF fitted, use it for search
                if self.tfidf_matrix is not None and len(self.documents) > 0:
                    logger.info(f"Using TF-IDF search for '{search_query}' (getting {search_limit} candidates)")
                    query_candidates = self._tfidf_search(search_query, search_limit, 0)  # Always start from 0 for initial search
                else:
                    # Fallback to simple text search
                    logger.info(f"Using simple text search for '{search_query}' (getting {search_limit} candidates)")
                    query_candidates = self._simple_text_search(search_query, search_limit)
                
                # Add unique candidates
                for candidate in query_candidates:
                    if candidate['id'] not in seen_ids:
                        all_candidates.append(candidate)
                        seen_ids.add(candidate['id'])
            
            # Sort combined candidates by score
            all_candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
            candidates = all_candidates
            
            if not candidates:
                return [], {'ai_reranking_used': False, 'message': 'No results found', 'total_results': 0}
            
            # Step 2: AI Reranking (if enabled and LLM client available)
            if enable_ai_reranking and self.llm_client:
                logger.info(f"🤖 Applying AI reranking to {len(candidates)} results...")
                
                # For pagination to work with AI reranking, we need to rerank enough candidates
                # to cover the requested offset + limit
                rerank_limit = max(20, offset + limit + 10)  # Rerank enough to cover pagination
                top_candidates = candidates[:min(rerank_limit, len(candidates))]
                
                try:
                    reranking_result = self.llm_client.rerank_results(
                        query=query,
                        results=top_candidates,
                        custom_instructions=ai_reranking_instructions,
                        ai_weight=ai_weight
                    )
                    
                    reranked = reranking_result['results']
                    metadata = reranking_result['metadata']
                    
                    # Ensure total_results is included in metadata
                    metadata['total_results'] = len(candidates)
                    
                    # Apply offset and return top N after reranking
                    paginated_results = reranked[offset:offset + limit]
                    logger.info(f"✅ AI reranking successful, returning {len(paginated_results)} results (offset={offset}, limit={limit})")
                    logger.info(f"🔍 AI RERANKING DEBUG: total_candidates={len(candidates)}, reranked_count={len(reranked)}, paginated_count={len(paginated_results)}")
                    return paginated_results, metadata
                    
                except Exception as e:
                    logger.error(f"AI reranking failed: {e}, falling back to TF-IDF results")
                    # Fall through to return TF-IDF results with proper pagination
                    paginated_results = candidates[offset:offset + limit]
                    logger.info(f"🔍 TF-IDF FALLBACK DEBUG: total_candidates={len(candidates)}, offset={offset}, limit={limit}, paginated_count={len(paginated_results)}")
                    return paginated_results, {
                        'ai_reranking_used': False,
                        'reason': f'AI reranking failed: {str(e)}',
                        'total_results': len(candidates)
                    }
            else:
                if not enable_ai_reranking:
                    logger.info("AI reranking disabled, using TF-IDF results")
                elif not self.llm_client:
                    logger.warning("LLM client not available, using TF-IDF results")
            
            # No AI reranking, return TF-IDF results with offset
            paginated_results = candidates[offset:offset + limit]
            logger.info(f"🔍 TF-IDF DEBUG: total_candidates={len(candidates)}, offset={offset}, limit={limit}, paginated_count={len(paginated_results)}")
            return paginated_results, {
                'ai_reranking_used': False,
                'reason': 'AI reranking disabled or unavailable',
                'total_results': len(candidates)
            }
            
        except Exception as e:
            logger.error(f"Error in search: {e}")
            return [], {'error': str(e), 'total_results': 0}
    
    async def search_with_answer(self, query: str, limit: int = 5, offset: int = 0, custom_instructions: str = "") -> Dict[str, Any]:
        """Search and generate AI answer."""
        try:
            # Get search results (without AI reranking for answer generation to save cost)
            results, search_metadata = await self.search(query, limit, offset, enable_ai_reranking=False)
            
            if not results:
                return {
                    'query': query,
                    'answer': "I couldn't find any relevant information to answer your question.",
                    'sources': [],
                    'source_count': 0,
                    'total_results': 0
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
                'source_count': len(results),
                'total_results': search_metadata.get('total_results', len(results))
            }
            
        except Exception as e:
            logger.error(f"Error in search with answer: {e}")
            return {
                'query': query,
                'answer': "I encountered an error while generating an answer.",
                'sources': [],
                'source_count': 0,
                'total_results': 0
            }
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get semantic embedding for text using OpenAI API or fallback."""
        try:
            # Try OpenAI embeddings first (if API key available)
            if hasattr(settings, 'openai_api_key') and settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=settings.openai_api_key)
                    response = client.embeddings.create(
                        model="text-embedding-3-small",
                        input=text[:8000]  # Limit input length
                    )
                    embedding = response.data[0].embedding
                    
                    # Pad or truncate to 384 dimensions
                    if len(embedding) < 384:
                        embedding = embedding + [0.0] * (384 - len(embedding))
                    else:
                        embedding = embedding[:384]
                    
                    return embedding
                except Exception as e:
                    logger.warning(f"OpenAI embedding failed: {e}, using fallback")
            
            # Use Sentence Transformers if available
            if self.embedding_model is not None:
                logger.debug(f"Generating semantic embedding for text (length: {len(text)} chars)")
                
                # Generate real semantic embedding
                embedding = self.embedding_model.encode(
                    text,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
                
                # Ensure it's exactly 384 dimensions (model outputs 384)
                if len(embedding) < 384:
                    # Pad if needed
                    embedding = np.pad(embedding, (0, 384 - len(embedding)), mode='constant')
                elif len(embedding) > 384:
                    # Truncate if needed
                    embedding = embedding[:384]
                
                return embedding.tolist()
            
            else:
                # Fallback to hash-based embedding if Sentence Transformers not available
                logger.warning("Using hash-based embedding fallback (install sentence-transformers for better quality)")
                return self._hash_based_embedding(text)
                
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            # Return zero vector as last resort
            return [0.0] * 384
    
    def _hash_based_embedding(self, text: str) -> List[float]:
        """Fallback hash-based embedding (not semantic, only for demo)."""
        try:
            import hashlib
            
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
            logger.error(f"Error in hash-based embedding: {e}")
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
    
    def _tfidf_search(self, query: str, limit: int, offset: int = 0) -> List[Dict[str, Any]]:
        """Perform TF-IDF based search with offset support."""
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
            
            # Apply offset and limit to get the correct slice
            start_idx = offset
            end_idx = offset + limit
            paginated_similarities = similarities[start_idx:end_idx]
            
            results = []
            for i, (doc_idx, score) in enumerate(paginated_similarities):
                if score > 0:  # Only include results with positive similarity
                    doc = self.documents[doc_idx]
                    result = {
                        'id': doc['id'],
                        'title': doc['title'],
                        'url': doc['url'],
                        'excerpt': doc['excerpt'],
                        'type': doc.get('type', 'post'),  # Include post type!
                        'date': doc.get('date', ''),
                        'author': doc.get('author', ''),
                        'categories': doc.get('categories', []),
                        'tags': doc.get('tags', []),
                        'content': doc.get('content', ''),
                        'word_count': doc.get('word_count', 0),
                        'featured_image': doc.get('featured_image', ''),
                        'featured_media': doc.get('featured_media', 0),
                        'score': float(score),
                        'relevance': 'high' if score > 0.1 else 'medium' if score > 0.05 else 'low'
                    }
                    results.append(result)
            
            logger.info(f"TF-IDF search: query='{query}', offset={offset}, limit={limit}, results={len(results)}")
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
                        'type': doc.get('type', 'post'),  # Include post type!
                        'date': doc.get('date', ''),
                        'author': doc.get('author', ''),
                        'categories': doc.get('categories', []),
                        'tags': doc.get('tags', []),
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

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
from constants import (
    EMBEDDING_DIMENSION,
    TFIDF_MAX_FEATURES,
    TFIDF_NGRAM_MIN,
    TFIDF_NGRAM_MAX,
    MIN_CONTENT_LENGTH,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    INDEX_BATCH_SIZE,
    MAX_SEARCH_RESULTS_FOR_ANSWER,
    MIN_RERANK_CANDIDATES,
    RERANK_BUFFER_SIZE,
    MAX_RESULT_LIMIT,
    RELEVANCE_HIGH_THRESHOLD,
    RELEVANCE_MEDIUM_THRESHOLD,
    RELEVANCE_LOW_THRESHOLD,
    OPENAI_EMBEDDING_MODEL,
    MAX_LLM_INPUT_LENGTH,
    DEFAULT_EMBEDDING_MODEL
)

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
            max_features=TFIDF_MAX_FEATURES,
            stop_words='english',
            ngram_range=(TFIDF_NGRAM_MIN, TFIDF_NGRAM_MAX)
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
            chunker = ContentChunker(chunk_size=DEFAULT_CHUNK_SIZE, overlap=DEFAULT_CHUNK_OVERLAP)
            chunked_documents = chunker.chunk_documents(documents)
            
            logger.info(f"After chunking: {len(chunked_documents)} total documents/chunks")
            
            # Prepare documents for indexing
            processed_docs = []
            document_texts = []
            
            # OPTIMIZATION: Batch embedding generation for better performance
            logger.info(f"Generating embeddings for {len(chunked_documents)} documents in batches of 50...")
            
            # Prepare all texts first
            doc_text_map = {}
            for doc in chunked_documents:
                combined_text = f"{doc['title']} {doc['content']}"
                document_texts.append(combined_text)
                doc_text_map[id(doc)] = combined_text
            
            # Generate embeddings in batches for efficiency
            batch_size = 50
            doc_embeddings = {}
            
            for i in range(0, len(chunked_documents), batch_size):
                batch_docs = chunked_documents[i:i+batch_size]
                batch_texts = [doc_text_map[id(doc)] for doc in batch_docs]
                
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(chunked_documents)-1)//batch_size + 1} ({len(batch_texts)} docs)")
                
                try:
                    # Batch encode using sentence-transformers (MUCH faster than individual!)
                    if SENTENCE_TRANSFORMERS_AVAILABLE and hasattr(settings, 'openai_api_key') and settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
                        # Try OpenAI batch API first
                        try:
                            embeddings = await self._generate_openai_embedding_batch(batch_texts)
                            for doc, emb in zip(batch_docs, embeddings):
                                doc_embeddings[id(doc)] = emb
                        except Exception as e:
                            logger.warning(f"OpenAI batch failed: {e}, falling back to local model")
                            # Fall back to local batch
                            embeddings = await self._generate_local_embedding_batch(batch_texts)
                            for doc, emb in zip(batch_docs, embeddings):
                                doc_embeddings[id(doc)] = emb
                    elif SENTENCE_TRANSFORMERS_AVAILABLE:
                        # Use local model with batch
                        embeddings = await self._generate_local_embedding_batch(batch_texts)
                        for doc, emb in zip(batch_docs, embeddings):
                            doc_embeddings[id(doc)] = emb
                    else:
                        logger.warning("No embedding service available, using zero vectors")
                        for doc in batch_docs:
                            doc_embeddings[id(doc)] = [0.0] * EMBEDDING_DIMENSION
                            
                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}, using zero vectors")
                    for doc in batch_docs:
                        doc_embeddings[id(doc)] = [0.0] * EMBEDDING_DIMENSION
            
            for doc in chunked_documents:
                try:
                    # Get pre-generated embedding
                    embedding = doc_embeddings.get(id(doc), [0.0] * EMBEDDING_DIMENSION)
                    
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
            
            # Store in Qdrant for hybrid search (if available)
            try:
                if self.qdrant_manager:
                    # Create collection first if it doesn't exist
                    logger.info("Ensuring Qdrant collection exists...")
                    self.qdrant_manager.create_collection()
                    
                    # Upsert documents to Qdrant (converts to proper format internally)
                    self.qdrant_manager.upsert_documents(processed_docs)
                    logger.info(f"Successfully indexed {len(processed_docs)} documents in Qdrant")
                else:
                    logger.warning("Qdrant not available - skipping vector storage")
            except Exception as e:
                logger.warning(f"Could not index to Qdrant (using TF-IDF only): {e}")
            
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
            if limit > MAX_RESULT_LIMIT:
                limit = MAX_RESULT_LIMIT
            
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
                rerank_limit = max(MIN_RERANK_CANDIDATES, offset + limit + RERANK_BUFFER_SIZE)
                top_candidates = candidates[:min(rerank_limit, len(candidates))]
                
                try:
                    # Use async version for better performance
                    reranking_result = await self.llm_client.rerank_results_async(
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
                    # Use top N results for answer generation
                    top_results = results[:MAX_SEARCH_RESULTS_FOR_ANSWER]
                    answer = self.llm_client.generate_answer(query, top_results, custom_instructions)
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
    
    async def generate_content_based_alternative_queries(self, query: str, search_results: List[Dict[str, Any]], max_alternatives: int = 5) -> List[str]:
        """
        Generate alternative queries based ONLY on the actual content in search results.
        This ensures alternative queries will find relevant content because they're based on what exists.
        
        Args:
            query: Original search query
            search_results: List of search results with titles, excerpts, content
            max_alternatives: Maximum number of alternative queries to generate
            
        Returns:
            List of alternative queries based on content analysis
        """
        try:
            if not search_results or len(search_results) == 0:
                logger.debug("No search results to analyze for alternative queries")
                return []
            
            if not self.llm_client:
                logger.debug("LLM client not available for content-based alternative query generation")
                return []
            
            # Extract content from top results
            top_results = search_results[:min(10, len(search_results))]  # Analyze top 10 results
            
            # Build context from results
            results_context = []
            for i, result in enumerate(top_results, 1):
                title = result.get('title', '')
                excerpt = result.get('excerpt', '') or result.get('content', '')[:300]
                result_type = result.get('type', 'unknown')
                
                results_context.append(f"""
Result {i}:
- Title: {title}
- Type: {result_type}
- Content: {excerpt}
""")
            
            results_text = "\n".join(results_context)
            
            # Prompt LLM to generate alternative queries based ONLY on this content
            prompt = f"""
You are a search query expert. I searched for: "{query}" and got these results:

{results_text}

Generate 3-5 alternative search queries that users might use to find SIMILAR content to what's shown here.

CRITICAL RULES:
1. ONLY use terms, topics, and concepts that appear in the search results above
2. Do NOT suggest queries about content that doesn't exist in the results
3. Use different phrasings, synonyms, or related terms that appear in these results
4. Make the queries diverse - cover different aspects shown in the results
5. Ensure each alternative query would likely find similar or related content

Return ONLY the queries, one per line, without numbering or bullet points.
"""
            
            # Call LLM
            logger.info(f"Generating content-based alternative queries for: '{query}'")
            
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a search query expansion expert that generates alternative queries based ONLY on provided content."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.5,  # Moderate temperature for diversity while staying grounded
                max_tokens=200
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse the alternative queries
            alternative_queries = [q.strip() for q in result.split('\n') if q.strip()]
            
            # Remove empty queries and limit to max_alternatives
            alternative_queries = [q for q in alternative_queries if q][:max_alternatives]
            
            logger.info(f"Generated {len(alternative_queries)} content-based alternative queries: {alternative_queries}")
            
            return alternative_queries
            
        except Exception as e:
            logger.error(f"Error generating content-based alternative queries: {e}")
            return []  # Return empty list on error, don't break search
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get semantic embedding for text using OpenAI API or fallback."""
        try:
            # Try OpenAI embeddings first (if API key available)
            if hasattr(settings, 'openai_api_key') and settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=settings.openai_api_key)
                    response = client.embeddings.create(
                        model=OPENAI_EMBEDDING_MODEL,
                        input=text[:MAX_LLM_INPUT_LENGTH]
                    )
                    embedding = response.data[0].embedding
                    
                    # Pad or truncate to target dimension
                    if len(embedding) < EMBEDDING_DIMENSION:
                        embedding = embedding + [0.0] * (EMBEDDING_DIMENSION - len(embedding))
                    else:
                        embedding = embedding[:EMBEDDING_DIMENSION]
                    
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
                
                # Ensure it's exactly the target dimension
                if len(embedding) < EMBEDDING_DIMENSION:
                    # Pad if needed
                    embedding = np.pad(embedding, (0, EMBEDDING_DIMENSION - len(embedding)), mode='constant')
                elif len(embedding) > EMBEDDING_DIMENSION:
                    # Truncate if needed
                    embedding = embedding[:EMBEDDING_DIMENSION]
                
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
            
            # Pad or truncate to exactly the target dimension
            while len(embedding) < EMBEDDING_DIMENSION:
                embedding.append(0.0)
            embedding = embedding[:EMBEDDING_DIMENSION]
            
            return embedding
                
        except Exception as e:
            logger.error(f"Error in hash-based embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * EMBEDDING_DIMENSION
    
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
            
            # Use vectors_count as the primary metric (total vectors stored)
            # indexed_vectors_count is about HNSW index status, which may be deferred
            vectors_count = collection_info.get('vectors_count', 0)
            indexed_vectors_count = collection_info.get('indexed_vectors_count', 0)
            
            # If indexed_vectors_count is 0 but we have vectors, it means indexing is deferred
            # Still show the actual vector count
            vectors_stored = vectors_count if vectors_count > 0 else indexed_vectors_count
            
            return {
                'collection_name': self.qdrant_manager.collection_name,
                'total_documents': collection_info.get('points_count', 0),
                'indexed_vectors': vectors_stored,  # Show actual vectors stored
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
            
            # Debug logging
            if similarities:
                logger.info(f"TF-IDF top 5 scores: {[f'{s[1]:.4f}' for s in similarities[:5]]}")
            else:
                logger.warning("TF-IDF returned no similarities")
            
            # Apply offset and limit to get the correct slice
            start_idx = offset
            end_idx = offset + limit
            paginated_similarities = similarities[start_idx:end_idx]
            
            results = []
            for i, (doc_idx, score) in enumerate(paginated_similarities):
                if score > 0:  # Only include results with positive similarity
                    logger.debug(f"Including result {i+1}: doc_idx={doc_idx}, score={score:.4f}")
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
    
    async def _generate_openai_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using available embedding service.
        Tries local model first (FREE), falls back to OpenAI if configured.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (384 dimensions)
        """
        # Try local sentence-transformers first (FREE and FAST!)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                return await self._generate_local_embedding(text)
            except Exception as e:
                logger.warning(f"Local embedding failed: {e}, trying OpenAI...")
        
        # Fall back to OpenAI if configured
        if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
            try:
                from openai import AsyncOpenAI
                
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                
                # Truncate text if too long
                max_length = 8000
                if len(text) > max_length:
                    text = text[:max_length]
                
                response = await client.embeddings.create(
                    model=settings.embed_model or "text-embedding-ada-002",
                    input=text
                )
                
                embedding = response.data[0].embedding
                
                # OpenAI returns 1536 dimensions, we need 384
                if len(embedding) != EMBEDDING_DIMENSION:
                    logger.debug(f"Adjusting embedding from {len(embedding)} to {EMBEDDING_DIMENSION} dimensions")
                    if len(embedding) < EMBEDDING_DIMENSION:
                        embedding = embedding + [0.0] * (EMBEDDING_DIMENSION - len(embedding))
                    else:
                        embedding = embedding[:EMBEDDING_DIMENSION]
                
                return embedding
                
            except Exception as e:
                logger.error(f"OpenAI embedding failed: {e}")
                raise
        
        # No embedding service available
        raise Exception("No embedding service available. Install sentence-transformers or configure OpenAI API key.")
    
    async def _generate_local_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using local sentence-transformers model.
        FREE, fast, and private!
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (384 dimensions)
        """
        try:
            if not hasattr(self, '_embedding_model'):
                logger.info("Loading local embedding model (all-MiniLM-L6-v2)...")
                from sentence_transformers import SentenceTransformer
                # This model outputs 384-dimensional embeddings (matches EMBEDDING_DIMENSION)
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ Local embedding model loaded successfully!")
            
            # Truncate text if too long
            max_length = 500  # sentence-transformers optimal length
            if len(text) > max_length:
                text = text[:max_length]
            
            # Generate embedding (runs on CPU/GPU locally)
            embedding = self._embedding_model.encode(text, convert_to_numpy=True)
            
            # Convert to list and ensure correct dimension
            embedding = embedding.tolist()
            
            if len(embedding) != EMBEDDING_DIMENSION:
                logger.warning(f"Embedding dimension mismatch: got {len(embedding)}, expected {EMBEDDING_DIMENSION}")
                if len(embedding) < EMBEDDING_DIMENSION:
                    embedding = embedding + [0.0] * (EMBEDDING_DIMENSION - len(embedding))
                else:
                    embedding = embedding[:EMBEDDING_DIMENSION]
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating local embedding: {e}")
            raise
    
    async def _generate_local_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch (MUCH faster!).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors (384 dimensions each)
        """
        try:
            if not hasattr(self, '_embedding_model'):
                logger.info("Loading local embedding model (all-MiniLM-L6-v2)...")
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ Local embedding model loaded successfully!")
            
            # Truncate texts if too long
            max_length = 500
            truncated_texts = [text[:max_length] if len(text) > max_length else text for text in texts]
            
            # Batch encode (sentence-transformers handles batching efficiently!)
            embeddings = self._embedding_model.encode(truncated_texts, convert_to_numpy=True, batch_size=32, show_progress_bar=False)
            
            # Convert to list and ensure correct dimensions
            results = []
            for emb in embeddings:
                emb_list = emb.tolist()
                if len(emb_list) != EMBEDDING_DIMENSION:
                    if len(emb_list) < EMBEDDING_DIMENSION:
                        emb_list = emb_list + [0.0] * (EMBEDDING_DIMENSION - len(emb_list))
                    else:
                        emb_list = emb_list[:EMBEDDING_DIMENSION]
                results.append(emb_list)
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating local embedding batch: {e}")
            raise
    
    async def _generate_openai_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using OpenAI (batch API).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors (1536 dimensions, converted to 384)
        """
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Truncate texts if too long
            max_length = 8000
            truncated_texts = [text[:max_length] if len(text) > max_length else text for text in texts]
            
            response = await client.embeddings.create(
                model=settings.embed_model or "text-embedding-ada-002",
                input=truncated_texts
            )
            
            # Convert to list and ensure correct dimensions
            results = []
            for item in response.data:
                embedding = item.embedding
                # OpenAI returns 1536 dimensions, we need 384
                if len(embedding) != EMBEDDING_DIMENSION:
                    if len(embedding) < EMBEDDING_DIMENSION:
                        embedding = embedding + [0.0] * (EMBEDDING_DIMENSION - len(embedding))
                    else:
                        embedding = embedding[:EMBEDDING_DIMENSION]
                results.append(embedding)
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding batch: {e}")
            raise
    
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

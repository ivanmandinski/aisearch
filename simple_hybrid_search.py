"""
Simplified hybrid search implementation without complex LlamaIndex dependencies.
"""
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlsplit, urlunsplit
import httpx
import asyncio
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
from config import settings
from query_analysis import analyze_query
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
    MAX_RERANK_CANDIDATES,
    TFIDF_HIGH_CONFIDENCE_THRESHOLD,
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
        # Embedding model will be lazily loaded on first use to reduce startup time
        # Use _embedding_model as private attribute, accessed via property
        self._embedding_model = None
        self._embedding_model_loaded = False
        self._last_query_analysis: Optional[Dict[str, Any]] = None
        
        # OPTIMIZATION: Cache query embeddings (queries repeat often)
        self._query_embedding_cache = {}
        self._query_cache_max_size = 1000  # Max cached queries
        
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
                # Check if API key is configured
                if not settings.cerebras_api_key or settings.cerebras_api_key.strip() == "":
                    logger.warning("⚠️ Cerebras API key not configured - AI reranking disabled")
                    logger.warning("   Set CEREBRAS_API_KEY environment variable to enable AI reranking")
                    self.llm_client = None
                else:
                    logger.info("Initializing CerebrasLLM...")
                    logger.info(f"   API Base: {settings.cerebras_api_base}")
                    logger.info(f"   Model: {settings.cerebras_model}")
                    self.llm_client = CerebrasLLM()
                    
                    # Test connection to ensure it's working
                    if hasattr(self.llm_client, 'test_connection'):
                        logger.info("Testing Cerebras API connection...")
                        connection_ok = self.llm_client.test_connection()
                        if connection_ok:
                            logger.info("✅ CerebrasLLM initialized and connection tested successfully")
                        else:
                            logger.warning("⚠️ CerebrasLLM initialized but connection test failed - reranking may not work")
                            logger.warning("   Check your CEREBRAS_API_KEY and CEREBRAS_API_BASE settings")
                    else:
                        logger.info("✅ CerebrasLLM initialized successfully (no connection test available)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize CerebrasLLM: {e}", exc_info=True)
                logger.error("   Check your CEREBRAS_API_KEY and CEREBRAS_API_BASE environment variables")
                self.llm_client = None
        else:
            if not CEREBRAS_AVAILABLE:
                logger.warning("⚠️ Cerebras LLM not available (CEREBRAS_AVAILABLE=False) - AI reranking disabled")
            elif CerebrasLLM is None:
                logger.warning("⚠️ CerebrasLLM class not available - AI reranking disabled")
            self.llm_client = None
        
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=TFIDF_MAX_FEATURES,
            stop_words='english',
            ngram_range=(TFIDF_NGRAM_MIN, TFIDF_NGRAM_MAX)
        )
        self.tfidf_matrix = None
        self.documents = []
        self.document_texts = []
        
        # Don't initialize with sample data on startup - only when actually needed
        # Sample data will be initialized lazily if no real data is available
    
    def _get_embedding_model(self):
        """
        Lazy-load the Sentence Transformer embedding model.
        This ensures we only load the model when actually needed, reducing startup time.
        """
        if self._embedding_model_loaded:
            return self._embedding_model
        
        # Mark as attempted to avoid repeated failures
        self._embedding_model_loaded = True
        
        if SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer is not None:
            try:
                logger.info("Loading Sentence Transformer embedding model (lazy load)...")
                # Use lightweight, fast model (80MB, 500+ sentences/sec)
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Sentence Transformer model loaded successfully (all-MiniLM-L6-v2)")
            except Exception as e:
                logger.error(f"Failed to initialize embedding model: {e}")
                self._embedding_model = None
        else:
            logger.debug("Sentence Transformers not available - will use hash-based fallback")
            self._embedding_model = None
        
        return self._embedding_model
    
    @property
    def embedding_model(self):
        """Property accessor for embedding model (lazy-loaded)."""
        return self._get_embedding_model()
    
    def _ensure_sample_data_initialized(self):
        """Lazily initialize with sample data only if no real data is available."""
        # Only initialize if we don't have any documents or TF-IDF matrix
        if self.tfidf_matrix is not None or len(self.documents) > 0:
            return  # Already have data, don't initialize sample data
        
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
            
            logger.debug(f"Lazily initialized with {len(sample_docs)} sample documents (no real data available)")
            
        except Exception as e:
            logger.error(f"Error initializing sample data: {e}")
    
    async def index_documents(self, documents: List[Dict[str, Any]], clear_existing: bool = True) -> bool:
        """Index documents for search with automatic chunking for long content.
        
        Args:
            documents: List of documents to index
            clear_existing: If True, clear existing collection before indexing (default: True)
        """
        try:
            logger.info(f"Indexing {len(documents)} documents...")
            
            if not documents:
                logger.warning("No documents to index")
                return False
            
            # Clear existing collection if requested (prevents duplicates)
            if clear_existing:
                logger.info("Clearing existing collection to prevent duplicates...")
                try:
                    cleared = self.qdrant_manager.clear_collection()
                    if cleared:
                        logger.info("✅ Successfully cleared existing collection")
                    else:
                        logger.warning("⚠️ Could not clear collection, proceeding with index anyway")
                except Exception as clear_error:
                    logger.warning(f"⚠️ Error clearing collection: {clear_error}, proceeding with index anyway")
                    # Continue indexing even if clear fails
            
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
        post_type_priority: Optional[List[str]] = None,
        behavioral_signals: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Perform search with optional AI reranking.
        
        Args:
            query: Search query
            limit: Number of results to return
            offset: Number of results to skip (for pagination)
            enable_ai_reranking: Whether to use AI reranking
            ai_weight: Weight for AI score (0-1), higher = more AI influence
            ai_reranking_instructions: Custom instructions for AI reranking
            post_type_priority: List of post types in priority order (e.g., ['post', 'page'])
            
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
            
            # Step 0.5: Analyze query intent and entities (with AI if available)
            query_analysis = analyze_query(query, llm_client=self.llm_client, use_ai=True)
            detected_intent = query_analysis.get('intent', 'general')
            intent_confidence = query_analysis.get('confidence', 0.0)
            self._last_query_analysis = query_analysis
            logger.info(
                f"🎯 Query intent detected: {detected_intent} "
                f"(confidence={intent_confidence:.2f}) | entities={query_analysis.get('entities', {})}"
            )
            
            # Generate intent-based instructions and combine with user's custom instructions
            intent_instructions = self._generate_intent_based_instructions(query, detected_intent)
            if intent_instructions and ai_reranking_instructions:
                # Combine user's custom instructions with intent-based instructions
                combined_instructions = f"{ai_reranking_instructions}\n\n{intent_instructions}"
                ai_reranking_instructions = combined_instructions
                logger.info(f"Combined user instructions with intent-based instructions")
            elif intent_instructions:
                # Use intent-based instructions only
                ai_reranking_instructions = intent_instructions
                logger.info(f"Using intent-based instructions: {detected_intent}")
            
            maps_input = behavioral_signals if settings.enable_ctr_boost else None
            behavioral_maps = self._prepare_behavioral_maps(maps_input)
            ctr_map = behavioral_maps.get('ctr', {})
            behavioral_enabled = settings.enable_ctr_boost and bool(ctr_map)
            
            # Get context-aware post type recommendations based on query analysis
            from query_analysis import get_recommended_post_types
            
            # Use context-aware recommendations, merging with admin-set priority
            context_recommended_priority = get_recommended_post_types(query_analysis, default_priority=post_type_priority)
            
            # If admin set a priority, we can either:
            # Option 1: Use context recommendations as override (smart mode)
            # Option 2: Use admin priority as base and apply context adjustments (hybrid mode)
            # Option 3: Always use admin priority (strict mode)
            # For now, we'll use hybrid mode: admin priority as base, context as smart adjustments
            
            if post_type_priority:
                # Admin priority exists - use it as base, but apply context adjustments
                # Context adjustments will reorder within admin's priority list
                logger.info(f"Admin priority (base): {post_type_priority}")
                logger.info(f"Context-recommended priority: {context_recommended_priority}")
                
                # Merge: prioritize types that are in both lists, maintaining admin order for others
                merged_priority = []
                seen = set()
                
                # First, add context-recommended types that are also in admin priority
                for pt in context_recommended_priority:
                    if pt in post_type_priority and pt not in seen:
                        merged_priority.append(pt)
                        seen.add(pt)
                
                # Then add remaining admin priority types
                for pt in post_type_priority:
                    if pt not in seen:
                        merged_priority.append(pt)
                        seen.add(pt)
                
                # Finally, add any context-recommended types not in admin priority
                for pt in context_recommended_priority:
                    if pt not in seen:
                        merged_priority.append(pt)
                        seen.add(pt)
                
                # Use merged priority
                effective_priority = merged_priority
                logger.info(f"Using merged priority (admin + context): {effective_priority}")
            else:
                # No admin priority - use context recommendations directly
                effective_priority = context_recommended_priority
                logger.info(f"Using context-recommended priority: {effective_priority}")
            
            # Store for use in post type priority application
            post_type_priority = effective_priority
            
            # Step 1: Get candidates using TF-IDF + Vector search with RRF
            # For pagination to work correctly, we need to get a larger set of results
            # and then apply offset/limit consistently
            
            # OPTIMIZATION: Reduce initial limit for faster search
            # We already cap reranking at MAX_RERANK_CANDIDATES (50), so we don't need as many initial results
            if enable_ai_reranking:
                # Reduced from limit * 3, 200 to limit * 2, 50 (matching MAX_RERANK_CANDIDATES)
                initial_limit = min(limit * 2, MAX_RERANK_CANDIDATES)
            else:
                initial_limit = limit
            search_limit = max(initial_limit, offset + limit + RERANK_BUFFER_SIZE)  # Get extra to ensure we have enough
            
            # Perform TF-IDF search
            tfidf_candidates = []
            
            # If we have TF-IDF fitted, use it for search
            if self.tfidf_matrix is not None and len(self.documents) > 0:
                logger.info(f"Using TF-IDF search for '{query}' (getting {search_limit} candidates)")
                tfidf_candidates = self._tfidf_search(query, search_limit, 0, query_analysis, behavioral_maps)  # Always start from 0 for initial search
                
                # If TF-IDF returns poor results (low scores), add simple text search as backup
                if len(tfidf_candidates) < 3 or (tfidf_candidates and tfidf_candidates[0]['score'] < 0.1):
                    logger.info(f"TF-IDF returned poor results, adding simple text search fallback for '{query}'")
                    simple_results = self._simple_text_search(query, search_limit // 2, query_analysis, behavioral_maps)
                    tfidf_candidates.extend(simple_results)
            else:
                # Fallback to simple text search
                logger.info(f"Using simple text search for '{query}' (getting {search_limit} candidates)")
                tfidf_candidates = self._simple_text_search(query, search_limit, query_analysis, behavioral_maps)
            
            # Perform Vector/Semantic search (if available)
            vector_candidates = []
            try:
                vector_candidates = await self._vector_search(query, search_limit)
                # Apply same boosting factors to vector results
                for result in vector_candidates:
                    field_boost = self._calculate_field_score(query, result, query_analysis)
                    freshness_boost = self._calculate_freshness_boost(result.get('date', ''))
                    category_tag_boost = self._calculate_category_tag_boost(query, result)
                    heading_anchor_boost = self._calculate_heading_anchor_boost(query, result)
                    taxonomy_depth_boost = self._calculate_taxonomy_depth_boost(result)
                    behavioral_boost = self._calculate_behavioral_boost(result, behavioral_maps)
                    result['score'] *= (
                        field_boost
                        * freshness_boost
                        * category_tag_boost
                        * heading_anchor_boost
                        * taxonomy_depth_boost
                        * behavioral_boost
                    )
                    meta = result.get('meta') if isinstance(result.get('meta'), dict) else {}
                    meta.setdefault('boost_debug', {})
                    meta['boost_debug'].update({
                        'field': round(field_boost, 3),
                        'freshness': round(freshness_boost, 3),
                        'category_tag': round(category_tag_boost, 3),
                        'heading_anchor': round(heading_anchor_boost, 3),
                        'taxonomy_depth': round(taxonomy_depth_boost, 3),
                        'behavioral': round(behavioral_boost, 3),
                    })
                    result['meta'] = meta
            except Exception as e:
                logger.warning(f"Vector search error: {e}, continuing with TF-IDF only")
            
            # Combine TF-IDF and Vector results using Reciprocal Rank Fusion (RRF)
            if vector_candidates and len(vector_candidates) > 0:
                logger.info(f"Combining {len(tfidf_candidates)} TF-IDF and {len(vector_candidates)} vector results using RRF")
                candidates = self._reciprocal_rank_fusion(tfidf_candidates, vector_candidates, k=60)
                logger.info(f"RRF combined to {len(candidates)} unique candidates")
            else:
                logger.info(f"Using TF-IDF results only ({len(tfidf_candidates)} candidates)")
                candidates = tfidf_candidates
            
            # Sort candidates by score (RRF score if available, otherwise original score)
            candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # Apply post type priority if specified
            if post_type_priority and len(post_type_priority) > 0:
                logger.info(f"Applying post type priority: {post_type_priority}")
                candidates = self._apply_post_type_priority(candidates, post_type_priority)
            
            if not candidates:
                return [], {
                    'ai_reranking_used': False,
                    'message': 'No results found',
                    'total_results': 0,
                    'query_context': query_analysis,
                    'query_intent': detected_intent,
                    'intent_instructions': intent_instructions if intent_instructions else None,
                    'behavioral_applied': behavioral_enabled,
                }
            
            # Step 2: AI Reranking (if enabled and LLM client available)
            # Ensure enable_ai_reranking is a proper boolean
            if isinstance(enable_ai_reranking, str):
                enable_ai_reranking = enable_ai_reranking.lower() in ('true', '1', 'yes', 'on', 'enabled')
            elif enable_ai_reranking is None:
                enable_ai_reranking = True  # Default to enabled
            else:
                enable_ai_reranking = bool(enable_ai_reranking)
            
            # Debug logging
            logger.info(f"🤖 AI Reranking Check:")
            logger.info(f"   enable_ai_reranking parameter: {enable_ai_reranking} (type: {type(enable_ai_reranking).__name__})")
            logger.info(f"   LLM client available: {self.llm_client is not None}")
            if self.llm_client:
                logger.info(f"   LLM client type: {type(self.llm_client).__name__}")
                logger.info(f"   LLM model: {getattr(self.llm_client, 'model', 'unknown')}")
            logger.info(f"   Will attempt reranking: {enable_ai_reranking and self.llm_client is not None}")
            
            if enable_ai_reranking and self.llm_client:
                # OPTIMIZATION: Skip reranking if top result has very high TF-IDF confidence
                # This saves time and cost for obvious matches
                skip_reranking = False
                if candidates and len(candidates) > 0:
                    top_score = candidates[0].get('score', 0.0)
                    if top_score >= TFIDF_HIGH_CONFIDENCE_THRESHOLD:
                        logger.info(f"⚡ Skipping AI reranking - top result has high TF-IDF confidence ({top_score:.3f} >= {TFIDF_HIGH_CONFIDENCE_THRESHOLD})")
                        skip_reranking = True
                
                if not skip_reranking:
                    logger.info(f"🤖 Applying AI reranking to {len(candidates)} results...")
                    
                    # OPTIMIZATION: Limit candidates sent to LLM for faster processing
                    # For pagination to work with AI reranking, we need to rerank enough candidates
                    # to cover the requested offset + limit, but cap at MAX_RERANK_CANDIDATES
                    rerank_limit = max(MIN_RERANK_CANDIDATES, offset + limit + RERANK_BUFFER_SIZE)
                    rerank_limit = min(rerank_limit, MAX_RERANK_CANDIDATES)  # Cap at max for performance
                    top_candidates = candidates[:min(rerank_limit, len(candidates))]
                    
                    logger.info(f"📊 Reranking top {len(top_candidates)} candidates (optimized from {len(candidates)} total)")
                    
                    try:
                        # Use async version for better performance
                        reranking_result = await self.llm_client.rerank_results_async(
                            query=query,
                            results=top_candidates,
                            custom_instructions=ai_reranking_instructions,
                            ai_weight=ai_weight,
                            post_type_priority=post_type_priority,
                            query_context=query_analysis
                        )
                        
                        reranked = reranking_result['results']
                        metadata = reranking_result['metadata']
                        
                        # Ensure total_results is included in metadata
                        metadata['total_results'] = len(candidates)
                        
                        # Add query intent info for admin tooltips
                        metadata['query_intent'] = detected_intent
                        metadata['intent_instructions'] = intent_instructions if intent_instructions else None
                        metadata['query_context'] = query_analysis
                        metadata['behavioral_applied'] = behavioral_enabled
                        metadata['behavioral_signals'] = behavioral_signals
                        
                        # Apply offset and return top N after reranking
                        paginated_results = reranked[offset:offset + limit]
                        
                        # Ensure ranking_explanation positions are updated for paginated results
                        for idx, result in enumerate(paginated_results):
                            if 'ranking_explanation' in result:
                                result['ranking_explanation']['final_position'] = offset + idx + 1
                        
                        logger.info(f"✅ AI reranking successful, returning {len(paginated_results)} results (offset={offset}, limit={limit})")
                        logger.info(f"🔍 AI RERANKING DEBUG: total_candidates={len(candidates)}, reranked_count={len(reranked)}, paginated_count={len(paginated_results)}")
                        
                        # Debug: Log if ranking_explanation exists
                        if paginated_results and 'ranking_explanation' in paginated_results[0]:
                            logger.info(f"✅ First paginated result has ranking_explanation: {paginated_results[0]['ranking_explanation']}")
                        else:
                            logger.warning(f"⚠️ First paginated result missing ranking_explanation!")
                        
                        return paginated_results, metadata
                        
                    except Exception as e:
                        logger.error(f"AI reranking failed: {e}, falling back to TF-IDF results")
                        # Fall through to return TF-IDF results with proper pagination
                        paginated_results = candidates[offset:offset + limit]
                        
                        # Add ranking explanation for fallback results
                        for idx, result in enumerate(paginated_results):
                            result['ranking_explanation'] = {
                                'tfidf_score': round(result.get('score', 0.0), 4),
                                'ai_score': None,
                                'ai_score_raw': None,
                                'hybrid_score': round(result.get('score', 0.0), 4),
                                'tfidf_weight': 1.0,
                                'ai_weight': 0.0,
                                'ai_reason': f'AI reranking failed: {str(e)}',
                                'post_type': result.get('type', 'unknown'),
                                'position_before_priority': None,
                                'final_position': idx + 1,
                                'post_type_priority': 9999,
                                'priority_order': post_type_priority if post_type_priority else []
                            }
                        
                        logger.info(f"🔍 TF-IDF FALLBACK DEBUG: total_candidates={len(candidates)}, offset={offset}, limit={limit}, paginated_count={len(paginated_results)}")
                        return paginated_results, {
                            'ai_reranking_used': False,
                            'reason': f'AI reranking failed: {str(e)}',
                            'total_results': len(candidates),
                            'query_context': query_analysis,
                            'query_intent': detected_intent,
                            'intent_instructions': intent_instructions if intent_instructions else None,
                            'behavioral_applied': behavioral_enabled,
                            'behavioral_signals': behavioral_signals,
                        }
                else:
                    # Skip reranking due to high TF-IDF confidence - return TF-IDF results
                    paginated_results = candidates[offset:offset + limit]
                    for idx, result in enumerate(paginated_results):
                        result['ranking_explanation'] = {
                            'tfidf_score': round(result.get('score', 0.0), 4),
                            'ai_score': None,
                            'ai_score_raw': None,
                            'hybrid_score': round(result.get('score', 0.0), 4),
                            'tfidf_weight': 1.0,
                            'ai_weight': 0.0,
                            'ai_reason': 'Skipped - high TF-IDF confidence',
                            'post_type': result.get('type', 'unknown'),
                            'position_before_priority': None,
                            'final_position': idx + 1,
                            'post_type_priority': 9999,
                            'priority_order': post_type_priority if post_type_priority else []
                        }
                    return paginated_results, {
                        'ai_reranking_used': False,
                        'reason': 'Skipped - high TF-IDF confidence',
                        'total_results': len(candidates),
                        'query_context': query_analysis,
                        'query_intent': detected_intent,
                        'intent_instructions': intent_instructions if intent_instructions else None,
                        'behavioral_applied': behavioral_enabled,
                        'behavioral_signals': behavioral_signals,
                    }
            else:
                if not enable_ai_reranking:
                    logger.info("❌ AI reranking disabled by parameter, using TF-IDF results")
                    disable_reason = "AI reranking disabled in settings"
                elif not self.llm_client:
                    logger.warning("❌ LLM client not available, using TF-IDF results")
                    if not CEREBRAS_AVAILABLE:
                        disable_reason = "Cerebras LLM not available (check imports)"
                    elif CerebrasLLM is None:
                        disable_reason = "CerebrasLLM class not imported"
                    else:
                        disable_reason = "LLM client not initialized (check Cerebras API key)"
                else:
                    disable_reason = "AI reranking unavailable"
            
            # No AI reranking, return TF-IDF results with offset
            paginated_results = candidates[offset:offset + limit]
            
            # Add ranking explanation even when AI reranking is disabled
            for idx, result in enumerate(paginated_results):
                result['ranking_explanation'] = {
                    'tfidf_score': round(result.get('score', 0.0), 4),
                    'ai_score': None,
                    'ai_score_raw': None,
                    'hybrid_score': round(result.get('score', 0.0), 4),
                    'tfidf_weight': 1.0,
                    'ai_weight': 0.0,
                    'ai_reason': disable_reason,
                    'post_type': result.get('type', 'unknown'),
                    'position_before_priority': None,
                    'final_position': idx + 1,
                    'post_type_priority': 9999,
                    'priority_order': post_type_priority if post_type_priority else []
                }
            
            logger.info(f"🔍 TF-IDF DEBUG: total_candidates={len(candidates)}, offset={offset}, limit={limit}, paginated_count={len(paginated_results)}")
            return paginated_results, {
                'ai_reranking_used': False,
                'reason': disable_reason,
                'total_results': len(candidates),
                'query_context': query_analysis,
                'query_intent': detected_intent,
            'intent_instructions': intent_instructions if intent_instructions else None,
            'behavioral_applied': behavioral_enabled,
            'behavioral_signals': behavioral_signals,
            }
            
        except Exception as e:
            logger.error(f"Error in search: {e}")
            return [], {
                'error': str(e),
                'total_results': 0,
                'query_context': query_analysis if 'query_analysis' in locals() else None,
            'query_intent': detected_intent if 'detected_intent' in locals() else None,
            'behavioral_applied': behavioral_enabled if 'behavioral_enabled' in locals() else False,
            'behavioral_signals': behavioral_signals if 'behavioral_signals' in locals() else None,
            }
    
    async def search_with_answer(
        self,
        query: str,
        limit: int = 5,
        offset: int = 0,
        custom_instructions: str = "",
        enable_ai_reranking: bool = True,
        behavioral_signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Search and generate AI answer."""
        try:
            # Get search results with AI reranking if enabled
            results, search_metadata = await self.search(
                query,
                limit,
                offset,
                enable_ai_reranking=enable_ai_reranking,
                behavioral_signals=behavioral_signals,
            )
            
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
            
            # Call LLM asynchronously to avoid blocking the event loop
            logger.info(f"Generating content-based alternative queries for: '{query}'")
            
            response = await self.llm_client.async_client.chat.completions.create(
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
    
    async def _get_query_embedding_cached(self, query: str) -> List[float]:
        """
        Get query embedding with caching (optimization for repeated queries).
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector (384 dimensions)
        """
        import hashlib
        
        # Normalize query for cache key (lowercase, strip whitespace)
        normalized_query = query.lower().strip()
        cache_key = hashlib.md5(normalized_query.encode()).hexdigest()
        
        # Check cache first
        if cache_key in self._query_embedding_cache:
            logger.debug(f"✅ Query embedding cache hit for: '{query[:50]}...'")
            return self._query_embedding_cache[cache_key]
        
        # Generate embedding
        embedding = await self._get_embedding(query)
        
        # Cache it (with size limit to prevent memory issues)
        if len(self._query_embedding_cache) >= self._query_cache_max_size:
            # Remove oldest entry (simple FIFO - remove first key)
            oldest_key = next(iter(self._query_embedding_cache))
            del self._query_embedding_cache[oldest_key]
            logger.debug(f"Evicted oldest query embedding from cache (cache full)")
        
        self._query_embedding_cache[cache_key] = embedding
        logger.debug(f"💾 Cached query embedding for: '{query[:50]}...'")
        
        return embedding
    
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
        """Get search statistics including post type breakdown."""
        try:
            collection_info = self.qdrant_manager.get_collection_info()
            
            # Get actual document count from Qdrant (points_count), not from in-memory sample data
            total_docs = collection_info.get('points_count', 0)
            
            # Ensure total_docs is an integer
            total_docs = int(total_docs) if total_docs is not None else 0
            
            # Use vectors_count as the primary metric (total vectors stored)
            # indexed_vectors_count is about HNSW index status, which may be deferred
            vectors_count = collection_info.get('vectors_count') or 0
            indexed_vectors_count = collection_info.get('indexed_vectors_count') or 0
            
            # Ensure they are integers (handle None values)
            vectors_count = int(vectors_count) if vectors_count is not None else 0
            indexed_vectors_count = int(indexed_vectors_count) if indexed_vectors_count is not None else 0
            
            # Determine the actual number of vectors stored
            # In Qdrant, each point typically has one vector, so if vectors_count is 0
            # but we have points, use points_count as a fallback
            if vectors_count > 0:
                vectors_stored = vectors_count
            elif indexed_vectors_count > 0:
                vectors_stored = indexed_vectors_count
            elif total_docs > 0:
                # Fallback: if we have points but no vector count, assume each point has a vector
                vectors_stored = total_docs
            else:
                vectors_stored = 0
            
            # Get post type breakdown by scrolling through all points
            post_type_breakdown = {}
            indexed_post_types = []
            
            if total_docs > 0 and self.qdrant_manager:
                try:
                    # Scroll through all points to get post type breakdown
                    from qdrant_client.models import ScrollRequest
                    offset = None
                    post_type_counts = {}
                    
                    while True:
                        scroll_result = self.qdrant_manager.client.scroll(
                            collection_name=self.qdrant_manager.collection_name,
                            limit=100,
                            offset=offset,
                            with_payload=True,
                            with_vectors=False
                        )
                        
                        points = scroll_result[0]
                        if not points:
                            break
                        
                        # Count by post type
                        for point in points:
                            if point.payload and 'type' in point.payload:
                                post_type = str(point.payload['type'])
                                post_type_counts[post_type] = post_type_counts.get(post_type, 0) + 1
                        
                        offset = scroll_result[1]
                        if offset is None:
                            break
                    
                    post_type_breakdown = post_type_counts
                    indexed_post_types = sorted(post_type_counts.keys())
                    
                    logger.debug(f"Post type breakdown: {post_type_breakdown}")
                    
                except Exception as e:
                    logger.warning(f"Could not get post type breakdown: {e}")
                    # Continue without breakdown
            
            # Log for debugging
            logger.debug(f"Stats: points_count={total_docs}, vectors_count={vectors_count}, indexed_vectors_count={indexed_vectors_count}, vectors_stored={vectors_stored}")
            
            return {
                'collection_name': self.qdrant_manager.collection_name,
                'total_documents': total_docs,
                'indexed_vectors': vectors_stored,  # Show actual vectors stored
                'status': collection_info.get('status', 'unknown'),
                'tfidf_fitted': self.tfidf_matrix is not None,
                'document_count': total_docs,  # Use Qdrant count, not in-memory sample count
                'post_type_breakdown': post_type_breakdown,  # Count per post type
                'indexed_post_types': indexed_post_types  # List of post types in index
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def _apply_post_type_priority(self, results: List[Dict[str, Any]], priority: List[str]) -> List[Dict[str, Any]]:
        """
        Re-sort results by post type priority.
        Results with higher priority post types will appear first within each score tier.
        ALL results are included, just reordered - no filtering.
        
        Args:
            results: List of search results
            priority: List of post types in priority order (e.g., ['post', 'page'])
            
        Returns:
            Re-sorted results (ALL results included, just reordered)
        """
        if not results or not priority:
            return results
        
        # Create priority map (lower index = higher priority)
        priority_map = {post_type: idx for idx, post_type in enumerate(priority)}
        
        # Get priority value for each result
        def get_priority(result):
            post_type = result.get('type', '')
            return priority_map.get(post_type, 9999)  # Unknown types go last
        
        # Sort by: existing score (descending), then priority (ascending - lower number = higher priority)
        # This maintains score-based ranking but prioritizes certain post types within same scores
        sorted_results = sorted(
            results,
            key=lambda x: (-x.get('score', 0.0), get_priority(x))
        )
        
        return sorted_results  # ALL results returned, just reordered
    
    def detect_query_intent(self, query: str) -> str:
        """
        Detect what the user is actually looking for based on query patterns.
        
        Args:
            query: Search query
            
        Returns:
            Intent type: 'person_name', 'service', 'howto', 'navigational', 'transactional', or 'general'
        """
        analysis = analyze_query(query, llm_client=self.llm_client, use_ai=True)
        intent = analysis.get('intent', 'general')
        self._last_query_analysis = analysis
        logger.info(f"Detected intent via shared analyzer: '{intent}' for query '{query}'")
        return intent
    
    def _generate_intent_based_instructions(self, query: str, intent: str) -> str:
        """
        Generate AI instructions based on detected query intent.
        
        Args:
            query: Search query
            intent: Detected intent ('person_name', 'service', etc.)
            
        Returns:
            AI instructions string
        """
        if intent == 'person_name':
            return f"""User is searching for a specific person: "{query}".

PRIORITY:
1. SCS Professionals profiles where the person's full name appears in the title
2. Biographical content about this specific person
3. Press releases, announcements, or news about this person

RULES:
- Only show results about THIS specific person
- Boost exact name matches in titles
- Do NOT include general articles unless they're specifically about this person
- If no professional profile exists, show news/articles about them"""
        
        elif intent == 'executive_role':
            return f"""User is asking about a specific executive role or position: "{query}".

PRIORITY:
1. SCS Professionals profiles where the person holds the specific role mentioned (CEO, President, etc.)
2. Press releases or announcements naming the person in that role
3. Professional profiles that mention the role in title or content

RULES:
- Prioritize profiles where the person is CURRENTLY in that role
- Look for role keywords: CEO, President, Executive, Chief, Director, Leader
- Boost results where role appears in title (e.g., "Doug Doerr, CEO")
- For "Who is the CEO?", the person currently holding that title should rank #1
- Recent announcements about role changes are highly relevant"""
        
        elif intent == 'service':
            return f"""User is looking for services or solutions related to: "{query}".

PRIORITY:
1. Service description pages that match the query
2. Solution offerings and capabilities
3. Service-specific landing pages

RULES:
- Prioritize actionable, practical service information
- Show what services are available
- Include capabilities and expertise areas
- Avoid general informational content unless highly relevant"""
        
        elif intent == 'howto':
            return f"""User needs actionable guidance on: "{query}".

PRIORITY:
1. Step-by-step guides and tutorials
2. Instructional content with actionable steps
3. "How to" articles with practical advice

RULES:
- Prioritize content with numbered steps or clear instructions
- Look for practical, actionable advice
- Skip theoretical content unless no practical guides exist
- Focus on "how to do X" rather than "what is X" """
        
        elif intent == 'navigational':
            return f"""User is looking for a specific page: "{query}".

PRIORITY:
1. Exact match for the page they're looking for
2. Related pages that might serve the same purpose

RULES:
- Match the navigation intent exactly
- Trust AI ranking (don't override with post type priority)
- Exact title matches should be #1"""
        
        elif intent == 'transactional':
            return f"""User wants to perform an action related to: "{query}".

PRIORITY:
1. Pages where they can complete the action
2. Service request pages
3. Download/application pages

RULES:
- Show pages where user can DO something (not just read about it)
- Prioritize actionable pages"""
        
        else:
            return ""  # General intent - use default behavior
    
    def _tfidf_search(
        self,
        query: str,
        limit: int,
        offset: int = 0,
        query_context: Optional[Dict[str, Any]] = None,
        behavioral_maps: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform TF-IDF based search with offset support."""
        try:
            # Lazy initialization: only initialize sample data if no real data is available
            if self.tfidf_matrix is None or len(self.documents) == 0:
                self._ensure_sample_data_initialized()
            
            # If still no data, return empty results
            if self.tfidf_matrix is None or len(self.documents) == 0:
                logger.warning("No documents available for TF-IDF search")
                return []
            
            if query_context is None:
                query_context = getattr(self, "_last_query_analysis", None)
            if behavioral_maps is None:
                behavioral_maps = {}
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
                    
                    # Apply multiple boosting factors
                    # 1. Field-based boosting (improved phrase matching)
                    field_boost = self._calculate_field_score(query, doc, query_context)
                    score *= field_boost
                    
                    # 2. Freshness/recency boosting
                    freshness_boost = self._calculate_freshness_boost(doc.get('date', ''))
                    score *= freshness_boost
                    
                    # 3. Category/tag matching boost
                    category_tag_boost = self._calculate_category_tag_boost(query, doc)
                    score *= category_tag_boost
                    
                    # 4. Heading/anchor boost
                    heading_anchor_boost = self._calculate_heading_anchor_boost(query, doc)
                    score *= heading_anchor_boost
                    
                    # 5. Taxonomy depth boost
                    taxonomy_depth_boost = self._calculate_taxonomy_depth_boost(doc)
                    score *= taxonomy_depth_boost

                    # 6. Behavioral (CTR) boost
                    behavioral_boost = self._calculate_behavioral_boost(doc, behavioral_maps)
                    score *= behavioral_boost
                    
                    logger.debug(
                        "Boosts applied - Field: %.2f, Freshness: %.2f, Category/Tag: %.2f, Heading/Anchor: %.2f, Taxonomy: %.2f, Behavioral: %.2f, Final: %.4f",
                        field_boost,
                        freshness_boost,
                        category_tag_boost,
                        heading_anchor_boost,
                        taxonomy_depth_boost,
                        behavioral_boost,
                        score,
                    )
                    
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
                    
                    if isinstance(doc.get('meta'), dict):
                        result_meta = dict(doc['meta'])
                    else:
                        result_meta = {}
                    result_meta['boost_debug'] = {
                        'field': round(field_boost, 3),
                        'freshness': round(freshness_boost, 3),
                        'category_tag': round(category_tag_boost, 3),
                        'heading_anchor': round(heading_anchor_boost, 3),
                        'taxonomy_depth': round(taxonomy_depth_boost, 3),
                        'behavioral': round(behavioral_boost, 3),
                    }
                    result['meta'] = result_meta
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
            # Use lazy-loaded embedding model (single instance)
            embedding_model = self.embedding_model
            if embedding_model is None:
                logger.warning("Embedding model not available, using hash-based fallback")
                return self._hash_based_embedding(text)
            
            # Truncate text if too long
            max_length = 500  # sentence-transformers optimal length
            if len(text) > max_length:
                text = text[:max_length]
            
            # Generate embedding (runs on CPU/GPU locally)
            embedding = embedding_model.encode(text, convert_to_numpy=True)
            
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
            # Use lazy-loaded embedding model (single instance)
            embedding_model = self.embedding_model
            if embedding_model is None:
                logger.warning("Embedding model not available, using hash-based fallback")
                return [self._hash_based_embedding(text) for text in texts]
            
            # Truncate texts if too long
            max_length = 500
            truncated_texts = [text[:max_length] if len(text) > max_length else text for text in texts]
            
            # Batch encode (sentence-transformers handles batching efficiently!)
            embeddings = embedding_model.encode(truncated_texts, convert_to_numpy=True, batch_size=32, show_progress_bar=False)
            
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
    
    def _simple_text_search(
        self,
        query: str,
        limit: int,
        query_context: Optional[Dict[str, Any]] = None,
        behavioral_maps: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform simple text-based search with partial word matching."""
        try:
            if query_context is None:
                query_context = getattr(self, "_last_query_analysis", None)
            if behavioral_maps is None:
                behavioral_maps = {}

            query_lower = query.lower().strip()
            if not query_lower:
                return []

            query_words = [word for word in query_lower.split() if len(word) >= 3]
            results = []
            
            for doc in self.documents:
                doc_title_lower = doc.get('title', '').lower()
                doc_content_lower = doc.get('content', '').lower()
                doc_excerpt_lower = doc.get('excerpt', '').lower()
                
                # Exact match (highest priority)
                exact_title_match = query_lower in doc_title_lower
                exact_content_match = query_lower in doc_content_lower
                exact_excerpt_match = query_lower in doc_excerpt_lower
                
                # Partial word match (handles "James Wals" → "James Walsh")
                partial_title_match = any(word in doc_title_lower for word in query_words if len(word) >= 4)
                partial_content_match = any(word in doc_content_lower for word in query_words if len(word) >= 4)
                partial_excerpt_match = any(word in doc_excerpt_lower for word in query_words if len(word) >= 4)
                
                # Calculate simple score
                score = 0.0
                if exact_title_match:
                    score += 5.0
                elif partial_title_match:
                    score += 2.0
                    
                if exact_excerpt_match:
                    score += 3.0
                elif partial_excerpt_match:
                    score += 1.0
                    
                if exact_content_match:
                    score += 2.0
                elif partial_content_match:
                    score += 0.5
                
                if score > 0:
                    # Normalize score to 0-1 range
                    normalized_score = score / 10.0
                    
                    # Apply boosting factors
                    field_boost = self._calculate_field_score(query, doc, query_context)
                    freshness_boost = self._calculate_freshness_boost(doc.get('date', ''))
                    category_tag_boost = self._calculate_category_tag_boost(query, doc)
                    behavioral_boost = self._calculate_behavioral_boost(doc, behavioral_maps)
                    
                    final_score = (
                        normalized_score
                        * field_boost
                        * freshness_boost
                        * category_tag_boost
                        * behavioral_boost
                    )
                    
                    result = {
                        'id': doc.get('id'),
                        'title': doc.get('title'),
                        'url': doc.get('url'),
                        'excerpt': doc.get('excerpt'),
                        'type': doc.get('type', 'post'),
                        'date': doc.get('date', ''),
                        'author': doc.get('author', ''),
                        'categories': doc.get('categories', []),
                        'tags': doc.get('tags', []),
                        'score': float(final_score),
                        'relevance': 'high' if final_score >= 0.5 else 'medium' if final_score >= 0.2 else 'low'
                    }
                    result['meta'] = {
                        'boost_debug': {
                            'field': round(field_boost, 3),
                            'freshness': round(freshness_boost, 3),
                            'category_tag': round(category_tag_boost, 3),
                            'behavioral': round(behavioral_boost, 3),
                        }
                    }
                    results.append(result)
            
            # Sort by score and limit results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error in simple text search: {e}")
            return []

    def _calculate_freshness_boost(self, doc_date: str) -> float:
        """
        Boost recent content (decay over time).
        
        Args:
            doc_date: Document date string (ISO format)
            
        Returns:
            Boost multiplier (1.0 = no boost, >1.0 = boosted)
        """
        if not doc_date:
            return 1.0
        
        try:
            from datetime import datetime, timezone
            
            # Parse date (handle various formats)
            try:
                if 'T' in doc_date:
                    doc_datetime = datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
                else:
                    doc_datetime = datetime.strptime(doc_date, '%Y-%m-%d')
                    doc_datetime = doc_datetime.replace(tzinfo=timezone.utc)
            except ValueError:
                # Try other formats
                try:
                    doc_datetime = datetime.strptime(doc_date, '%Y-%m-%d %H:%M:%S')
                    doc_datetime = doc_datetime.replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(f"Could not parse date: {doc_date}, using no boost")
                    return 1.0
            
            # Calculate days old
            now = datetime.now(doc_datetime.tzinfo)
            days_old = (now - doc_datetime).days
            
            # Boost: 2.0x for <7 days, 1.8x for <30 days, 1.5x for <90 days, 1.2x for <180 days, 1.0x for older
            if days_old < 7:
                return 2.0  # Very recent content gets strong boost
            elif days_old < 30:
                return 1.8  # Recent content gets strong boost
            elif days_old < 90:
                return 1.5  # Moderately recent content gets moderate boost
            elif days_old < 180:
                return 1.2  # Somewhat recent content gets slight boost
            return 1.0
            
        except Exception as e:
            logger.warning(f"Error calculating freshness boost: {e}")
            return 1.0
    
    def _calculate_field_score(
        self,
        query: str,
        doc: Dict[str, Any],
        query_context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate field-based relevance score with improved phrase matching.
        
        Args:
            query: Search query
            doc: Document dictionary
            query_context: Optional heuristic analysis (intent/entities)
            
        Returns:
            Boost multiplier
        """
        if query_context is None:
            query_context = getattr(self, "_last_query_analysis", None)

        query_lower = query.lower().strip()
        query_words = [word for word in query_lower.split() if len(word) >= 3]
        query_word_set = set(query_words)
        
        title_lower = doc.get('title', '').lower()
        excerpt_lower = (doc.get('excerpt', '') or '').lower()
        content_lower = doc.get('content', '').lower()
        doc_type = (doc.get('type') or '').lower()
        
        boost = 0.0
        
        # Exact phrase match in title (highest priority)
        if query_lower in title_lower:
            boost += 2.0  # Base 1.0 + 2.0 = 3.0 (previous behaviour)
        # All words in title (phrase match)
        elif query_word_set and query_word_set.issubset(set(title_lower.split())):
            boost += 1.2
        # Some words in title
        elif any(word in title_lower for word in query_words):
            boost += 0.6
        
        # Excerpt matches (medium priority)
        if query_lower in excerpt_lower:
            boost += 0.8
        elif any(word in excerpt_lower for word in query_words):
            boost += 0.3
        
        # Content matches (lowest priority)
        if query_word_set and any(word in content_lower for word in query_words):
            boost += 0.15

        # Meta keywords / custom fields
        meta = doc.get('meta', {}) if isinstance(doc.get('meta'), dict) else {}
        meta_text_parts: List[str] = []
        if meta:
            for key in (
                'focus_keyword',
                'focus_keywords',
                'keywords',
                'yoast_focus_keyword',
                'yoast_focus_keywords',
                'topics',
                'key_topics',
                'summary',
                'meta_keywords',
            ):
                value = meta.get(key)
                if not value:
                    continue
                if isinstance(value, str):
                    meta_text_parts.append(value.lower())
                elif isinstance(value, (list, tuple, set)):
                    meta_text_parts.extend(str(item).lower() for item in value if item)
        if isinstance(doc.get('custom_fields'), dict):
            for val in doc['custom_fields'].values():
                if isinstance(val, str):
                    meta_text_parts.append(val.lower())
                elif isinstance(val, (list, tuple, set)):
                    meta_text_parts.extend(str(item).lower() for item in val if item)
        meta_text = " ".join(meta_text_parts)
        if meta_text:
            if query_lower and query_lower in meta_text:
                boost += 0.6
            elif any(word in meta_text for word in query_words):
                boost += 0.25

        # Entity-aware boosts (services, people, locations, regulatory topics)
        if query_context:
            entities = query_context.get('entities', {})
            primary_entities = query_context.get('primary_entities', [])

            service_entities = [
                str(service).lower()
                for service in entities.get('services', [])
                if isinstance(service, str)
            ]
            for service in service_entities:
                if not service:
                    continue
                if service in query_lower:
                    continue  # already covered above
                if (
                    service in title_lower
                    or service in excerpt_lower
                    or (meta_text and service in meta_text)
                    or service in content_lower[:2000]
                ):
                    boost += 0.75
                    break

            # If query focuses on services, prefer service content types
            if 'services' in primary_entities and doc_type in {'page', 'scs-services'}:
                boost += 0.4

            people_entities = [
                str(person).lower()
                for person in entities.get('people', [])
                if isinstance(person, str)
            ]
            if people_entities:
                for person in people_entities:
                    if person and person in title_lower:
                        boost += 0.6
                        break
                if doc_type in {'scs-professionals', 'staff', 'team'}:
                    boost += 0.4

            location_entities = [
                str(loc).lower()
                for loc in entities.get('locations', [])
                if isinstance(loc, str)
            ]
            for location in location_entities:
                if not location or location in query_lower:
                    continue
                if (
                    location in title_lower
                    or location in excerpt_lower
                    or (meta_text and location in meta_text)
                ):
                    boost += 0.3
                    break

            regulatory_entities = [
                str(term).lower()
                for term in entities.get('regulatory', [])
                if isinstance(term, str)
            ]
            if regulatory_entities:
                for term in regulatory_entities:
                    if term and (term in title_lower or term in meta_text):
                        boost += 0.25
                        break

        # Return boost multiplier (minimum 1.0, capped to avoid runaway boosts)
        return max(1.0, min(1.0 + boost, 4.0))
        
        # Return boost multiplier (minimum 1.0)
        return max(score, 1.0)
    
    def _calculate_category_tag_boost(self, query: str, doc: Dict[str, Any]) -> float:
        """
        Boost if query matches categories or tags.
        
        Args:
            query: Search query
            doc: Document dictionary
            
        Returns:
            Boost multiplier (capped at 1.5x)
        """
        query_lower = query.lower().strip()
        query_words = set(query_lower.split())
        
        boost = 1.0
        
        # Check categories
        categories = doc.get('categories', [])
        for cat in categories:
            if isinstance(cat, dict):
                cat_slug = cat.get('slug', '').lower()
                cat_name = cat.get('name', '').lower()
            else:
                cat_slug = str(cat).lower()
                cat_name = cat_slug
            
            if query_lower in cat_slug or query_lower in cat_name:
                boost += 0.3
            elif any(word in cat_slug or word in cat_name for word in query_words if len(word) >= 3):
                boost += 0.15
        
        # Check tags
        tags = doc.get('tags', [])
        for tag in tags:
            if isinstance(tag, dict):
                tag_slug = tag.get('slug', '').lower()
                tag_name = tag.get('name', '').lower()
            else:
                tag_slug = str(tag).lower()
                tag_name = tag_slug
            
            if query_lower in tag_slug or query_lower in tag_name:
                boost += 0.2
            elif any(word in tag_slug or word in tag_name for word in query_words if len(word) >= 3):
                boost += 0.1
        
        return min(boost, 1.5)  # Cap at 1.5x
    
    def _create_normalized_score_map(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Normalize scores (0-1) for a list of results.
        """
        if not results:
            return {}
        
        scores = []
        ids = []
        for result in results:
            doc_id = str(result.get('id', ''))
            if not doc_id:
                continue
            ids.append(doc_id)
            scores.append(max(float(result.get('score', 0.0)), 0.0))
        
        if not scores:
            return {}
        
        max_score = max(scores)
        min_score = min(scores)
        if max_score == min_score:
            return {doc_id: 1.0 for doc_id in ids}
        
        return {
            doc_id: (score - min_score) / (max_score - min_score)
            for doc_id, score in zip(ids, scores)
        }
    
    def _calculate_heading_anchor_boost(self, query: str, doc: Dict[str, Any]) -> float:
        """
        Boost documents where the query appears in headings or anchor text.
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return 1.0
        
        query_words = [word for word in query_lower.split() if len(word) >= 3]
        boost = 1.0
        
        meta = doc.get('meta', {})
        headings: List[str] = []
        if isinstance(meta, dict):
            headings_meta = meta.get('headings')
            if isinstance(headings_meta, list):
                headings.extend(str(h) for h in headings_meta)
        
        content = doc.get('content', '') or ''
        if content and not headings:
            raw_headings = re.findall(r'<h[1-3][^>]*>(.*?)</h[1-3]>', content, flags=re.IGNORECASE | re.DOTALL)
            headings.extend(raw_headings)
        
        def clean_text(text: str) -> str:
            # Remove HTML tags and collapse whitespace
            cleaned = re.sub(r'<[^>]+>', ' ', text)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return cleaned.strip().lower()
        
        headings = [clean_text(h) for h in headings if isinstance(h, str) and h.strip()]
        
        for heading in headings:
            if not heading:
                continue
            if query_lower in heading:
                boost += 0.35
                break
            elif all(word in heading for word in query_words):
                boost += 0.25
                break
        
        # Anchor text
        anchors = re.findall(r'<a[^>]*>(.*?)</a>', content, flags=re.IGNORECASE | re.DOTALL) if content else []
        for anchor in anchors:
            anchor_text = clean_text(anchor)
            if not anchor_text:
                continue
            if query_lower in anchor_text:
                boost += 0.2
                break
            elif any(word in anchor_text for word in query_words):
                boost += 0.1
                break
        
        return min(boost, 1.6)
    
    def _calculate_taxonomy_depth_boost(self, doc: Dict[str, Any]) -> float:
        """
        Boost documents that belong to deep taxonomy hierarchies (more specific content).
        """
        depth_score = 0.0
        
        for taxonomy in ('categories', 'tags'):
            terms = doc.get(taxonomy, [])
            for term in terms:
                parent_id = None
                slug = None
                if isinstance(term, dict):
                    parent_id = term.get('parent')
                    slug = term.get('slug') or term.get('path')
                else:
                    slug = str(term)
                
                if parent_id:
                    depth_score += 0.1
                if isinstance(slug, str):
                    # Count nesting indicators (e.g., waste/services/hazardous)
                    depth_score += 0.05 * slug.count('/')
                    depth_score += 0.05 * slug.count('>')
        
        return min(1.0 + depth_score, 1.4)

    def _prepare_behavioral_maps(
        self,
        signals: Optional[Dict[str, Any]],
    ) -> Dict[str, Dict[str, float]]:
        maps: Dict[str, Dict[str, float]] = {
            'ctr': {}
        }
        if not signals:
            return maps

        ctr_payload = signals.get('ctr')
        if isinstance(ctr_payload, dict):
            ctr_items = ctr_payload.get('items', [])
            ctr_map: Dict[str, float] = {}
            for item in ctr_items:
                url = item.get('url')
                weight = item.get('weight')
                if not url or weight is None:
                    continue
                try:
                    normalized_url = self._normalize_url(url)
                    ctr_weight = float(weight)
                except (ValueError, TypeError):
                    continue
                if not normalized_url or ctr_weight <= 0:
                    continue
                ctr_map[normalized_url] = min(max(ctr_weight, 0.0), 1.0)
            maps['ctr'] = ctr_map

        return maps

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        try:
            parsed = urlsplit(url)
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            path = parsed.path.rstrip('/') or '/'
            return urlunsplit((scheme, netloc, path, '', ''))
        except Exception:
            return url.strip().lower().rstrip('/')

    def _calculate_behavioral_boost(
        self,
        doc: Dict[str, Any],
        behavioral_maps: Dict[str, Dict[str, float]],
    ) -> float:
        boost = 1.0
        if not behavioral_maps:
            return boost

        url = doc.get('url')
        if url:
            norm_url = self._normalize_url(url)
        else:
            norm_url = ""

        ctr_map = behavioral_maps.get('ctr', {})
        if norm_url and norm_url in ctr_map:
            ctr_weight = min(max(float(ctr_map[norm_url]), 0.0), 1.0)
            boost *= 1.0 + (ctr_weight * 0.75)

        return boost
    
    def _reciprocal_rank_fusion(self, results1: List[Dict[str, Any]], results2: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
        """
        Combine two result lists using Reciprocal Rank Fusion (RRF).
        
        Args:
            results1: First result list (e.g., TF-IDF results)
            results2: Second result list (e.g., Vector results)
            k: RRF constant (default 60)
            
        Returns:
            Combined and reranked results
        """
        scores = {}
        lexical_norm_map = self._create_normalized_score_map(results1)
        vector_norm_map = self._create_normalized_score_map(results2)
        
        # Score results from first list
        for rank, result in enumerate(results1, 1):
            doc_id = str(result.get('id', ''))
            if not doc_id:
                continue
            entry = scores.setdefault(doc_id, {'doc': result.copy(), 'rrf_score': 0.0})
            entry['rrf_score'] += 1.0 / (k + rank)
            doc_entry = entry['doc']
            doc_entry['lexical_score'] = result.get('score', 0.0)
            doc_entry['lexical_score_normalized'] = lexical_norm_map.get(doc_id, 0.0)
            doc_entry['lexical_rank'] = rank
        
        # Score results from second list
        for rank, result in enumerate(results2, 1):
            doc_id = str(result.get('id', ''))
            if not doc_id:
                continue
            entry = scores.setdefault(doc_id, {'doc': result.copy(), 'rrf_score': 0.0})
            entry['rrf_score'] += 1.0 / (k + rank)
            doc_entry = entry['doc']
            doc_entry.setdefault('lexical_score', 0.0)
            doc_entry.setdefault('lexical_score_normalized', 0.0)
            doc_entry['vector_score'] = result.get('score', 0.0)
            doc_entry['vector_score_normalized'] = vector_norm_map.get(doc_id, 0.0)
            doc_entry['vector_rank'] = rank
        
        # Sort by RRF score
        combined = sorted(scores.values(), key=lambda x: x['rrf_score'], reverse=True)
        
        # Update scores in results
        for item in combined:
            doc_entry = item['doc']
            doc_entry.setdefault('lexical_score', 0.0)
            doc_entry.setdefault('lexical_score_normalized', 0.0)
            doc_entry.setdefault('vector_score', 0.0)
            doc_entry.setdefault('vector_score_normalized', 0.0)
            doc_entry['rrf_score'] = item['rrf_score']
            # Use RRF score as base score, but preserve original score for reference
            if 'original_score' not in doc_entry:
                doc_entry['original_score'] = doc_entry.get('score', 0.0)
            doc_entry['score'] = item['rrf_score']
            fusion_details = doc_entry.get('fusion_details', {})
            fusion_details.update({
                'lexical_score_normalized': doc_entry.get('lexical_score_normalized'),
                'vector_score_normalized': doc_entry.get('vector_score_normalized'),
                'lexical_rank': doc_entry.get('lexical_rank'),
                'vector_rank': doc_entry.get('vector_rank'),
                'rrf_constant': k,
            })
            doc_entry['fusion_details'] = fusion_details
        
        return [item['doc'] for item in combined]
    
    async def _vector_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Perform vector/semantic search using embeddings.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        try:
            if not self.qdrant_manager:
                logger.debug("Qdrant manager not available, skipping vector search")
                return []
            
            # Generate query embedding
            query_embedding = await self._get_query_embedding_cached(query)
            
            # Check if embedding is valid (not all zeros)
            if all(x == 0.0 for x in query_embedding):
                logger.warning("Query embedding is all zeros, skipping vector search")
                return []
            
            # Get sparse vector for hybrid search
            sparse_vector = self._get_sparse_vector(query)
            
            # Perform hybrid search via Qdrant
            logger.info(f"Performing vector search for '{query}' (limit={limit})")
            vector_results = self.qdrant_manager.hybrid_search(
                query=query,
                dense_vector=query_embedding,
                sparse_vector=sparse_vector,
                limit=limit * 2,  # Get more for RRF combination
                alpha=0.6  # 60% semantic, 40% keyword
            )
            
            logger.info(f"Vector search returned {len(vector_results)} results")
            return vector_results
            
        except Exception as e:
            logger.warning(f"Vector search failed: {e}, continuing with TF-IDF only")
            return []
    
    def close(self):
        """Close the search system."""
        if self.qdrant_manager:
            self.qdrant_manager.close()

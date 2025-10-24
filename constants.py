"""
Constants and configuration values for the hybrid search system.
Centralizes all magic numbers and hardcoded values for easier maintenance.
"""

# ============================================================================
# SEARCH CONSTANTS
# ============================================================================

# Query constraints
MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 500
MIN_SEARCH_QUERY_LENGTH = 3  # For meaningful search tracking

# Result limits
MIN_RESULT_LIMIT = 1
MAX_RESULT_LIMIT = 100
DEFAULT_RESULT_LIMIT = 10

# Pagination
MAX_PAGINATION_OFFSET = 10000
MIN_OFFSET = 0

# ============================================================================
# EMBEDDING CONSTANTS
# ============================================================================

# Vector dimensions
EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2 dimension
OPENAI_EMBEDDING_DIMENSION = 1536  # OpenAI text-embedding-ada-002

# Embedding models
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# ============================================================================
# TF-IDF CONSTANTS
# ============================================================================

# TF-IDF configuration
TFIDF_MAX_FEATURES = 10000
TFIDF_NGRAM_MIN = 1
TFIDF_NGRAM_MAX = 2
TFIDF_MIN_SIMILARITY = 0.0  # Minimum similarity score to include

# ============================================================================
# AI RERANKING CONSTANTS
# ============================================================================

# AI reranking parameters
DEFAULT_AI_WEIGHT = 0.7  # 70% AI, 30% TF-IDF
MIN_AI_WEIGHT = 0.0
MAX_AI_WEIGHT = 1.0

# Reranking limits
MIN_RERANK_CANDIDATES = 20
RERANK_BUFFER_SIZE = 10  # Extra results to fetch for reranking

# AI scoring
AI_SCORE_MIN = 0
AI_SCORE_MAX = 100

# ============================================================================
# LLM CONSTANTS
# ============================================================================

# Temperature settings
TEMPERATURE_RERANKING = 0.1  # Very low for consistent scoring
TEMPERATURE_QUERY_REWRITE = 0.3  # Low but allows some creativity
TEMPERATURE_ANSWER_GENERATION = 0.2  # Low for factual answers
TEMPERATURE_QUERY_EXPANSION = 0.5  # Medium for diverse alternatives

# Token limits
MAX_TOKENS_RERANKING = 2000
MAX_TOKENS_QUERY_REWRITE = 500
MAX_TOKENS_ANSWER_GENERATION = 800
MAX_TOKENS_SUMMARIZATION = 300
MAX_TOKENS_KEYWORD_EXTRACTION = 200
MAX_TOKENS_QUERY_CLASSIFICATION = 300

# Context limits
MAX_LLM_INPUT_LENGTH = 8000  # Characters
MAX_SEARCH_RESULTS_FOR_ANSWER = 5  # Top N results to use for answer generation
MAX_EXCERPT_LENGTH = 500  # Characters for excerpts in context

# ============================================================================
# CONTENT PROCESSING CONSTANTS
# ============================================================================

# Chunking
DEFAULT_CHUNK_SIZE = 1000  # Characters
DEFAULT_CHUNK_OVERLAP = 200  # Characters
MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 5000

# Content limits
MAX_CONTENT_LENGTH = 10000  # Characters
MIN_CONTENT_LENGTH = 50  # Minimum content length to index
MIN_WORD_COUNT = 10  # Minimum words for valid content

# ============================================================================
# WORDPRESS FETCH CONSTANTS
# ============================================================================

# Pagination
WP_POSTS_PER_PAGE = 50  # Fetch batch size
WP_MAX_PAGES = 100  # Safety limit per post type
WP_MAX_TOTAL_ITEMS = 5000  # Per post type

# Timeouts
WP_REQUEST_TIMEOUT = 30.0  # Seconds
WP_KEEPALIVE_EXPIRY = 30.0  # Seconds

# Connection limits
WP_MAX_KEEPALIVE_CONNECTIONS = 20
WP_MAX_CONNECTIONS = 100

# ============================================================================
# INDEXING CONSTANTS
# ============================================================================

# Batch sizes
INDEX_BATCH_SIZE = 100  # Documents to index at once
VECTOR_UPSERT_BATCH_SIZE = 100  # Vectors to upsert at once

# Limits
MAX_DOCUMENTS_PER_REQUEST = 10000

# ============================================================================
# CACHE CONSTANTS
# ============================================================================

# Cache TTL (seconds)
CACHE_TTL_SHORT = 300  # 5 minutes
CACHE_TTL_MEDIUM = 1800  # 30 minutes
CACHE_TTL_LONG = 3600  # 1 hour
CACHE_TTL_VERY_LONG = 86400  # 24 hours

# Cache keys
CACHE_PREFIX_SEARCH = "search:"
CACHE_PREFIX_SUGGEST = "suggest:"
CACHE_PREFIX_HEALTH = "health:"

# ============================================================================
# RATE LIMITING CONSTANTS
# ============================================================================

# Rate limits (requests per minute)
RATE_LIMIT_SEARCH = 60  # 60 searches per minute
RATE_LIMIT_INDEX = 10  # 10 index operations per minute
RATE_LIMIT_SUGGEST = 120  # 120 suggestions per minute

# ============================================================================
# READING TIME CONSTANTS
# ============================================================================

# Average reading speed
WORDS_PER_MINUTE = 200  # Average reading speed
MIN_READING_TIME = 1  # Minimum reading time in minutes

# ============================================================================
# RESPONSE CODES
# ============================================================================

# HTTP status codes (for clarity)
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503

# ============================================================================
# RELEVANCE SCORING CONSTANTS
# ============================================================================

# Relevance thresholds
RELEVANCE_HIGH_THRESHOLD = 0.8
RELEVANCE_MEDIUM_THRESHOLD = 0.6
RELEVANCE_LOW_THRESHOLD = 0.4

# Score weights for different match types
TITLE_MATCH_WEIGHT = 3.0
EXCERPT_MATCH_WEIGHT = 2.0
CONTENT_MATCH_WEIGHT = 1.0

# ============================================================================
# COMPRESSION CONSTANTS
# ============================================================================

# GZip middleware
GZIP_MIN_SIZE = 1000  # Bytes - only compress responses larger than 1KB
GZIP_COMPRESSION_LEVEL = 6  # Balanced compression level (1-9)

# ============================================================================
# PRICING CONSTANTS (for cost tracking)
# ============================================================================

# Cerebras pricing (approximate)
CEREBRAS_COST_PER_MILLION_TOKENS = 0.10  # $0.10 per 1M tokens

# OpenAI pricing (approximate)
OPENAI_EMBEDDING_COST_PER_MILLION_TOKENS = 0.02  # text-embedding-3-small

# ============================================================================
# SUGGESTION CONSTANTS
# ============================================================================

# Suggestion limits
MIN_SUGGESTION_QUERY_LENGTH = 2
MAX_SUGGESTIONS = 10
DEFAULT_SUGGESTIONS = 5

# Query expansion
MAX_QUERY_EXPANSIONS = 5
DEFAULT_QUERY_EXPANSIONS = 3

# ============================================================================
# IMAGE CONSTANTS
# ============================================================================

# Image formats
SUPPORTED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'webp', 'gif']

# Image URL validation
MIN_IMAGE_URL_LENGTH = 10

# ============================================================================
# ANALYTICS CONSTANTS
# ============================================================================

# Session tracking
SESSION_ID_LENGTH = 32

# Query filtering
IGNORE_QUERIES = ['test', 'debug', 'admin']  # Don't track these queries

# ============================================================================
# MISC CONSTANTS
# ============================================================================

# Date formats
DATE_FORMAT_ISO = "%Y-%m-%dT%H:%M:%S"
DATE_FORMAT_DISPLAY = "%b %d, %Y"

# Truncation
AI_ANSWER_TRUNCATE_WORDS = 25  # Words to show before "show more"

# Fallback values
FALLBACK_AUTHOR = "Unknown"
FALLBACK_POST_TYPE = "post"

# API versioning
API_VERSION_HEADER = "X-API-Version"


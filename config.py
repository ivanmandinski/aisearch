"""
Configuration module for the hybrid search system.

This module defines all application settings loaded from environment variables.
Settings are validated using Pydantic for type safety.
"""
import os
from typing import Optional, Literal, List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables or .env file.
    Type validation is performed automatically by Pydantic.
    """
    
    # ========================================================================
    # QDRANT CONFIGURATION
    # ========================================================================
    
    qdrant_url: str = "http://localhost:6333"
    """Qdrant vector database URL"""
    
    qdrant_api_key: Optional[str] = None
    """Optional Qdrant API key for authentication"""
    
    qdrant_collection_name: str = "wordpress_content"
    """Name of the Qdrant collection for storing vectors"""
    
    # ========================================================================
    # CEREBRAS LLM CONFIGURATION
    # ========================================================================
    
    cerebras_api_base: str = "https://api.cerebras.ai/v1"
    """Cerebras API base URL"""
    
    cerebras_api_key: str = ""
    """Cerebras API key for authentication"""
    
    cerebras_model: str = "cerebras-llama-2-7b-chat"
    """Cerebras model name to use"""
    
    # ========================================================================
    # OPENAI CONFIGURATION (for embeddings)
    # ========================================================================
    
    openai_api_key: str = ""
    """OpenAI API key for embedding generation"""
    
    # ========================================================================
    # EMBEDDING AND SPARSE MODELS
    # ========================================================================
    
    embed_model: str = "text-embedding-ada-002"
    """Embedding model name"""
    
    sparse_model: str = "tfidf"
    """Sparse vector model (tfidf or bm25)"""
    
    # ========================================================================
    # WORDPRESS CONFIGURATION
    # ========================================================================
    
    wordpress_url: str = ""
    """WordPress site URL"""
    
    wordpress_username: str = ""
    """WordPress username for API authentication"""
    
    wordpress_password: str = ""
    """WordPress application password"""
    
    wordpress_api_url: str = ""
    """WordPress REST API endpoint URL"""
    
    # ========================================================================
    # API CONFIGURATION
    # ========================================================================
    
    api_host: str = "0.0.0.0"
    """API server host"""
    
    api_port: int = 8000
    """API server port"""
    
    api_title: str = "Hybrid Search API"
    """API title for documentation"""
    
    api_version: str = "2.15.1"
    """API version number"""
    
    # ========================================================================
    # SEARCH CONFIGURATION
    # ========================================================================
    
    max_search_results: int = 10
    """Maximum number of search results to return"""
    
    search_timeout: int = 30
    """Search operation timeout in seconds"""
    
    embedding_dimension: int = 384
    """Dimension of embedding vectors"""
    
    chunk_size: int = 512
    """Size of content chunks for indexing"""
    
    default_site_base: str = ""
    """Default base URL for the site"""
    
    search_page_title: str = "Hybrid Search"
    """Title for the search page"""

    enable_ctr_boost: bool = True
    """Toggle analytics-driven CTR boosting."""

    enable_ai_rerank: bool = True
    """Globally enable/disable AI reranking support."""

    # ========================================================================
    # INTENT KEYWORD CUSTOMIZATION
    # ========================================================================

    intent_service_keywords: List[str] = []
    """Additional keywords/phrases that should signal service intent."""

    intent_sector_keywords: List[str] = []
    """Additional keywords/phrases that should signal sector/industry intent."""

    intent_navigational_keywords: List[str] = []
    """Additional keywords/phrases that should signal navigational intent."""

    intent_transactional_keywords: List[str] = []
    """Additional keywords/phrases that should signal transactional intent."""

    # ========================================================================
    # AI INSTRUCTIONS CONFIGURATION
    # ========================================================================
    
    ai_instructions: str = ""
    """Default AI instructions for answer generation"""
    
    strict_ai_answer_mode: bool = True
    """If True, AI answers only use search results (no external knowledge)"""
    
    @field_validator('sparse_model')
    @classmethod
    def normalize_sparse_model(cls, v: str) -> str:
        """
        Normalize sparse_model value to handle various input formats.
        
        Handles cases like:
        - "Qdrant/bm25" -> "bm25"
        - "BM25" -> "bm25"
        - "TF-IDF" -> "tfidf"
        """
        if not v:
            return "tfidf"  # Default
        
        # Extract model name if prefixed (e.g., "Qdrant/bm25" -> "bm25")
        if '/' in v:
            v = v.split('/')[-1]
        
        # Normalize to lowercase and remove hyphens
        v = v.lower().replace('-', '').replace('_', '')
        
        # Map common variations
        if v in ['bm25', 'bm-25']:
            return "bm25"
        elif v in ['tfidf', 'tf-idf', 'tf_idf']:
            return "tfidf"
        
        # Default to tfidf if unrecognized
        return "tfidf"
    
    @field_validator(
        'intent_service_keywords',
        'intent_sector_keywords',
        'intent_navigational_keywords',
        'intent_transactional_keywords',
        mode='before',
    )
    @classmethod
    def parse_keyword_list(cls, v):
        """
        Normalize comma-separated environment values into string lists.
        """
        if v in (None, "", []):
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(',') if item.strip()]
        if isinstance(v, (set, tuple)):
            return [str(item).strip() for item in v if str(item).strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings: Settings = Settings()

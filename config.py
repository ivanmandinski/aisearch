"""
Configuration module for the hybrid search system.
"""
import os
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection_name: str = "wordpress_content"
    
    # Cerebras LLM Configuration
    cerebras_api_base: str = "https://api.cerebras.ai/v1"
    cerebras_api_key: str
    cerebras_model: str = "cerebras-llama-2-7b-chat"
    
    # Embedding and Sparse Models
    embed_model: str = "text-embedding-ada-002"
    sparse_model: str = "tfidf"
    
    # WordPress Configuration
    wordpress_url: str
    wordpress_username: str
    wordpress_password: str
    wordpress_api_url: str
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "Hybrid Search API"
    api_version: str = "1.0.0"
    
    # Search Configuration
    max_search_results: int = 10
    search_timeout: int = 30
    embedding_dimension: int = 1536
    chunk_size: int = 512
    default_site_base: str = ""
    search_page_title: str = "Hybrid Search"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

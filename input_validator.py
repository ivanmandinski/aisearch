"""
Comprehensive input validation module for the hybrid search API.
"""
import re
import html
import logging
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator, root_validator
import bleach

logger = logging.getLogger(__name__)


class SearchRequestValidator(BaseModel):
    """Enhanced search request validation with comprehensive security checks."""
    
    query: str = Field(..., min_length=1, max_length=255, description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, le=10000, description="Number of results to skip")
    include_answer: bool = Field(default=False, description="Whether to include LLM-generated answer")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")
    ai_instructions: Optional[str] = Field(default=None, max_length=1000, description="Custom AI instructions")
    enable_ai_reranking: bool = Field(default=True, description="Whether to use AI reranking")
    ai_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for AI score")
    ai_reranking_instructions: str = Field(default="", max_length=1000, description="Custom AI reranking instructions")
    
    @validator('query')
    def validate_query(cls, v):
        """Validate and sanitize search query."""
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', v.strip())
        
        # Check for SQL injection patterns
        sql_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter)\s+',
            r'(or|and)\s+\d+\s*=\s*\d+',
            r';\s*(drop|delete|insert|update)',
            r'--\s*$',
            r'/\*.*\*/',
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning(f"Potential SQL injection attempt detected: {v}")
                raise ValueError('Invalid query format')
        
        # Check for XSS patterns
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning(f"Potential XSS attempt detected: {v}")
                raise ValueError('Invalid query format')
        
        # Limit consecutive special characters
        if re.search(r'[^\w\s]{3,}', sanitized):
            raise ValueError('Query contains too many special characters')
        
        return sanitized
    
    @validator('ai_instructions', 'ai_reranking_instructions')
    def validate_instructions(cls, v):
        """Validate AI instructions for security."""
        if not v:
            return v
        
        # Remove HTML tags and potentially dangerous content
        cleaned = bleach.clean(v, tags=[], strip=True)
        
        # Check for command injection patterns
        dangerous_patterns = [
            r'`[^`]*`',  # Backticks
            r'\$\([^)]*\)',  # Command substitution
            r';\s*\w+',  # Command chaining
            r'\|\s*\w+',  # Pipe commands
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, cleaned):
                logger.warning(f"Potential command injection in instructions: {v}")
                raise ValueError('Invalid instructions format')
        
        return cleaned
    
    @validator('filters')
    def validate_filters(cls, v):
        """Validate search filters."""
        if not v:
            return v
        
        allowed_filter_keys = {'type', 'author', 'categories', 'tags', 'date', 'sort'}
        sanitized_filters = {}
        
        for key, value in v.items():
            if key not in allowed_filter_keys:
                logger.warning(f"Invalid filter key: {key}")
                continue
            
            # Sanitize filter values
            if isinstance(value, str):
                sanitized_value = re.sub(r'[<>"\']', '', value.strip())
                if len(sanitized_value) > 100:
                    sanitized_value = sanitized_value[:100]
                sanitized_filters[key] = sanitized_value
            elif isinstance(value, list):
                sanitized_list = []
                for item in value:
                    if isinstance(item, str):
                        sanitized_item = re.sub(r'[<>"\']', '', item.strip())
                        if len(sanitized_item) <= 100:
                            sanitized_list.append(sanitized_item)
                sanitized_filters[key] = sanitized_list
            else:
                sanitized_filters[key] = value
        
        return sanitized_filters
    
    @root_validator
    def validate_request_size(cls, values):
        """Validate overall request size and complexity."""
        query = values.get('query', '')
        ai_instructions = values.get('ai_instructions', '')
        ai_reranking_instructions = values.get('ai_reranking_instructions', '')
        
        total_length = len(query) + len(ai_instructions) + len(ai_reranking_instructions)
        
        if total_length > 2000:
            raise ValueError('Request too large')
        
        return values


class IndexRequestValidator(BaseModel):
    """Validation for index requests."""
    
    force_reindex: bool = Field(default=False, description="Force reindexing")
    post_types: Optional[List[str]] = Field(default=None, description="Post types to index")
    
    @validator('post_types')
    def validate_post_types(cls, v):
        """Validate post types."""
        if not v:
            return v
        
        allowed_types = {'post', 'page', 'attachment', 'revision', 'nav_menu_item'}
        sanitized_types = []
        
        for post_type in v:
            if isinstance(post_type, str):
                sanitized_type = re.sub(r'[^a-zA-Z0-9_-]', '', post_type.strip())
                if sanitized_type and len(sanitized_type) <= 50:
                    sanitized_types.append(sanitized_type)
        
        return sanitized_types if sanitized_types else None


class DocumentValidator(BaseModel):
    """Validation for document indexing."""
    
    id: str = Field(..., min_length=1, max_length=100, description="Document ID")
    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    slug: str = Field(..., min_length=1, max_length=200, description="Document slug")
    type: str = Field(..., min_length=1, max_length=50, description="Document type")
    url: str = Field(..., min_length=1, max_length=500, description="Document URL")
    content: str = Field(..., min_length=1, max_length=50000, description="Document content")
    
    @validator('id', 'slug', 'type')
    def validate_identifiers(cls, v):
        """Validate document identifiers."""
        # Only allow alphanumeric, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid identifier format')
        return v
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, v):
            raise ValueError('Invalid URL format')
        return v
    
    @validator('title', 'content')
    def validate_text_content(cls, v):
        """Validate and sanitize text content."""
        # Remove potentially dangerous HTML
        cleaned = bleach.clean(v, tags=['p', 'br', 'strong', 'em', 'ul', 'ol', 'li'], strip=True)
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, cleaned, re.IGNORECASE):
                logger.warning(f"Suspicious content detected: {v[:100]}...")
                # Remove the suspicious content
                cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned


def validate_search_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize search request data."""
    try:
        validator = SearchRequestValidator(**data)
        return validator.dict()
    except Exception as e:
        logger.error(f"Search request validation failed: {e}")
        raise ValueError(f"Invalid request: {str(e)}")


def validate_index_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize index request data."""
    try:
        validator = IndexRequestValidator(**data)
        return validator.dict()
    except Exception as e:
        logger.error(f"Index request validation failed: {e}")
        raise ValueError(f"Invalid request: {str(e)}")


def validate_document(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize document data."""
    try:
        validator = DocumentValidator(**data)
        return validator.dict()
    except Exception as e:
        logger.error(f"Document validation failed: {e}")
        raise ValueError(f"Invalid document: {str(e)}")


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """Sanitize a string for safe use."""
    if not isinstance(text, str):
        return str(text)
    
    # Remove HTML tags
    cleaned = bleach.clean(text, tags=[], strip=True)
    
    # Remove dangerous characters
    cleaned = re.sub(r'[<>"\']', '', cleaned)
    
    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned.strip()


def validate_api_key(api_key: str) -> bool:
    """Validate API key format."""
    if not api_key:
        return False
    
    # Check for reasonable API key format (alphanumeric, length 20-100)
    if not re.match(r'^[a-zA-Z0-9_-]{20,100}$', api_key):
        return False
    
    return True


def validate_ip_address(ip: str) -> bool:
    """Validate IP address format."""
    import ipaddress
    
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def rate_limit_check(ip: str, endpoint: str, limit: int = 100, window: int = 3600) -> bool:
    """Check if IP is within rate limits."""
    # This would integrate with Redis or similar for production
    # For now, return True (no rate limiting)
    return True

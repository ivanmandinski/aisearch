"""
Comprehensive error response handling for the hybrid search API.
Provides standardized error responses with proper status codes and helpful messages.
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ErrorCode:
    """Standard error codes for the application."""
    # Client errors (4xx)
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_QUERY = "INVALID_QUERY"
    QUERY_TOO_SHORT = "QUERY_TOO_SHORT"
    QUERY_TOO_LONG = "QUERY_TOO_LONG"
    INVALID_LIMIT = "INVALID_LIMIT"
    INVALID_OFFSET = "INVALID_OFFSET"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Server errors (5xx)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SEARCH_FAILED = "SEARCH_FAILED"
    INDEX_FAILED = "INDEX_FAILED"
    LLM_ERROR = "LLM_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class SearchError(Exception):
    """Base exception for search-related errors."""
    
    def __init__(
        self, 
        message: str, 
        code: str = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(SearchError):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_REQUEST,
            status_code=400,
            details={**(details or {}), "field": field} if field else details
        )


class ServiceUnavailableError(SearchError):
    """Raised when a required service is unavailable."""
    
    def __init__(self, service: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Service unavailable: {service}",
            code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=503,
            details={**(details or {}), "service": service}
        )


class RateLimitError(SearchError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: Optional[int] = None):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details={"retry_after": retry_after} if retry_after else {}
        )


def create_error_response(
    error: Exception,
    request_id: Optional[str] = None,
    include_traceback: bool = False
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error: The exception that occurred
        request_id: Optional request ID for tracking
        include_traceback: Whether to include traceback (dev only)
    
    Returns:
        JSONResponse with error details
    """
    # Determine error details based on exception type
    if isinstance(error, SearchError):
        status_code = error.status_code
        error_code = error.code
        message = error.message
        details = error.details
    elif isinstance(error, HTTPException):
        status_code = error.status_code
        error_code = ErrorCode.INTERNAL_ERROR
        message = error.detail
        details = {}
    else:
        status_code = 500
        error_code = ErrorCode.INTERNAL_ERROR
        message = "An unexpected error occurred"
        details = {}
    
    # Build response body
    response_body: Dict[str, Any] = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }
    
    # Add optional fields
    if request_id:
        response_body["error"]["request_id"] = request_id
    
    if details:
        response_body["error"]["details"] = details
    
    if include_traceback:
        import traceback
        response_body["error"]["traceback"] = traceback.format_exc()
    
    # Log the error
    logger.error(
        f"Error response: {error_code} - {message}",
        extra={
            "error_code": error_code,
            "status_code": status_code,
            "request_id": request_id,
            "details": details
        }
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response_body
    )


def create_success_response(
    data: Any,
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        data: The response data
        message: Optional success message
        metadata: Optional metadata
    
    Returns:
        Standardized response dictionary
    """
    response: Dict[str, Any] = {
        "success": True,
        "data": data
    }
    
    if message:
        response["message"] = message
    
    if metadata:
        response["metadata"] = metadata
    
    return response


def validate_search_params(
    query: str,
    limit: int,
    offset: int = 0
) -> None:
    """
    Validate search parameters and raise ValidationError if invalid.
    
    Args:
        query: Search query string
        limit: Result limit
        offset: Result offset
    
    Raises:
        ValidationError: If parameters are invalid
    """
    # Validate query
    if not query or not query.strip():
        raise ValidationError("Query cannot be empty", field="query")
    
    if len(query) < 2:
        raise ValidationError(
            "Query must be at least 2 characters",
            field="query",
            details={"min_length": 2, "actual_length": len(query)}
        )
    
    if len(query) > 500:
        raise ValidationError(
            "Query exceeds maximum length",
            field="query",
            details={"max_length": 500, "actual_length": len(query)}
        )
    
    # Validate limit
    if limit < 1:
        raise ValidationError(
            "Limit must be at least 1",
            field="limit",
            details={"min_value": 1, "actual_value": limit}
        )
    
    if limit > 100:
        raise ValidationError(
            "Limit exceeds maximum value",
            field="limit",
            details={"max_value": 100, "actual_value": limit}
        )
    
    # Validate offset
    if offset < 0:
        raise ValidationError(
            "Offset cannot be negative",
            field="offset",
            details={"actual_value": offset}
        )


def validate_index_params(documents: list) -> None:
    """
    Validate index parameters.
    
    Args:
        documents: List of documents to index
    
    Raises:
        ValidationError: If parameters are invalid
    """
    if not documents:
        raise ValidationError("No documents provided", field="documents")
    
    if not isinstance(documents, list):
        raise ValidationError(
            "Documents must be a list",
            field="documents",
            details={"actual_type": type(documents).__name__}
        )
    
    if len(documents) > 10000:
        raise ValidationError(
            "Too many documents in single request",
            field="documents",
            details={"max_count": 10000, "actual_count": len(documents)}
        )


# HTTP status code helpers
def bad_request(message: str, **kwargs) -> JSONResponse:
    """Create a 400 Bad Request response."""
    return create_error_response(
        ValidationError(message, **kwargs)
    )


def not_found(message: str = "Resource not found") -> JSONResponse:
    """Create a 404 Not Found response."""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


def service_unavailable(service: str, **kwargs) -> JSONResponse:
    """Create a 503 Service Unavailable response."""
    return create_error_response(
        ServiceUnavailableError(service, **kwargs)
    )


def internal_error(message: str = "Internal server error", **kwargs) -> JSONResponse:
    """Create a 500 Internal Server Error response."""
    return create_error_response(
        SearchError(message, code=ErrorCode.INTERNAL_ERROR, status_code=500, **kwargs)
    )


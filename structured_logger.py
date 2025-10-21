"""
Comprehensive logging module for the hybrid search API.
Provides structured logging with different levels and contexts.
"""
import logging
import json
import time
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
import os
from contextvars import ContextVar

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
session_id_var: ContextVar[str] = ContextVar('session_id', default='')


class StructuredLogger:
    """Structured logger with context awareness."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with proper formatting."""
        if not self.logger.handlers:
            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)
            
            # Add file handler if LOG_FILE is set
            log_file = os.getenv('LOG_FILE')
            if log_file:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
    
    def _get_context(self) -> Dict[str, Any]:
        """Get current context information."""
        return {
            'request_id': request_id_var.get(''),
            'user_id': user_id_var.get(''),
            'session_id': session_id_var.get(''),
            'timestamp': datetime.utcnow().isoformat(),
        }
    
    def _log_structured(self, level: str, message: str, **kwargs):
        """Log structured message with context."""
        context = self._get_context()
        context.update(kwargs)
        
        log_data = {
            'level': level,
            'message': message,
            'context': context
        }
        
        if level == 'ERROR' and 'exception' in kwargs:
            log_data['traceback'] = traceback.format_exc()
        
        # Log as JSON for structured logging
        self.logger.log(getattr(logging, level), json.dumps(log_data))
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_structured('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_structured('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_structured('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_structured('DEBUG', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log_structured('CRITICAL', message, **kwargs)


class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self):
        self.logger = StructuredLogger('performance')
        self._timers: Dict[str, float] = {}
    
    def start_timer(self, operation: str) -> str:
        """Start timing an operation."""
        timer_id = f"{operation}_{int(time.time() * 1000)}"
        self._timers[timer_id] = time.time()
        return timer_id
    
    def end_timer(self, timer_id: str, **kwargs):
        """End timing and log performance."""
        if timer_id in self._timers:
            duration = time.time() - self._timers[timer_id]
            del self._timers[timer_id]
            
            self.logger.info(
                f"Performance: {timer_id.split('_')[0]} completed",
                duration_ms=round(duration * 1000, 2),
                **kwargs
            )
    
    def log_search_performance(self, query: str, result_count: int, duration: float, **kwargs):
        """Log search performance metrics."""
        self.logger.info(
            "Search performance",
            operation="search",
            query=query,
            result_count=result_count,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def log_api_performance(self, endpoint: str, method: str, status_code: int, duration: float, **kwargs):
        """Log API performance metrics."""
        self.logger.info(
            "API performance",
            operation="api_request",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )


class SecurityLogger:
    """Logger for security events."""
    
    def __init__(self):
        self.logger = StructuredLogger('security')
    
    def log_suspicious_query(self, query: str, reason: str, **kwargs):
        """Log suspicious search query."""
        self.logger.warning(
            "Suspicious query detected",
            event_type="suspicious_query",
            query=query,
            reason=reason,
            **kwargs
        )
    
    def log_rate_limit_exceeded(self, ip: str, endpoint: str, **kwargs):
        """Log rate limit exceeded."""
        self.logger.warning(
            "Rate limit exceeded",
            event_type="rate_limit",
            ip_address=ip,
            endpoint=endpoint,
            **kwargs
        )
    
    def log_authentication_failure(self, reason: str, **kwargs):
        """Log authentication failure."""
        self.logger.warning(
            "Authentication failure",
            event_type="auth_failure",
            reason=reason,
            **kwargs
        )
    
    def log_injection_attempt(self, query: str, pattern: str, **kwargs):
        """Log injection attempt."""
        self.logger.error(
            "Injection attempt detected",
            event_type="injection_attempt",
            query=query,
            pattern=pattern,
            **kwargs
        )


class BusinessLogger:
    """Logger for business metrics."""
    
    def __init__(self):
        self.logger = StructuredLogger('business')
    
    def log_search_event(self, query: str, result_count: int, has_results: bool, **kwargs):
        """Log search business event."""
        self.logger.info(
            "Search event",
            event_type="search",
            query=query,
            result_count=result_count,
            has_results=has_results,
            **kwargs
        )
    
    def log_zero_results(self, query: str, **kwargs):
        """Log zero results event."""
        self.logger.info(
            "Zero results",
            event_type="zero_results",
            query=query,
            **kwargs
        )
    
    def log_user_engagement(self, action: str, **kwargs):
        """Log user engagement event."""
        self.logger.info(
            "User engagement",
            event_type="engagement",
            action=action,
            **kwargs
        )


# Global logger instances
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()
business_logger = BusinessLogger()


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


def set_request_context(request_id: str, user_id: str = '', session_id: str = ''):
    """Set request context for logging."""
    request_id_var.set(request_id)
    user_id_var.set(user_id)
    session_id_var.set(session_id)


def clear_request_context():
    """Clear request context."""
    request_id_var.set('')
    user_id_var.set('')
    session_id_var.set('')


def log_exception(logger: StructuredLogger, message: str, exception: Exception, **kwargs):
    """Log exception with traceback."""
    logger.error(
        message,
        exception=str(exception),
        exception_type=type(exception).__name__,
        **kwargs
    )


def log_api_request(logger: StructuredLogger, method: str, endpoint: str, **kwargs):
    """Log API request."""
    logger.info(
        f"API Request: {method} {endpoint}",
        operation="api_request",
        method=method,
        endpoint=endpoint,
        **kwargs
    )


def log_api_response(logger: StructuredLogger, method: str, endpoint: str, status_code: int, duration: float, **kwargs):
    """Log API response."""
    logger.info(
        f"API Response: {method} {endpoint} - {status_code}",
        operation="api_response",
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=round(duration * 1000, 2),
        **kwargs
    )

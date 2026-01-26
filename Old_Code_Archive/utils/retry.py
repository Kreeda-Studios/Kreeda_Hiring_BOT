"""
Retry logic and circuit breakers for API calls and file operations.
"""

import time
from typing import Callable, TypeVar, Optional, Any
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

T = TypeVar('T')


# ==================== Retry Decorators ====================

def retry_api_call(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
    exponential_base: float = 2.0
):
    """
    Retry decorator for API calls with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        exponential_base: Base for exponential backoff
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=initial_wait, max=max_wait, exp_base=exponential_base),
            retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
            reraise=True
        )
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log retry attempt
                print(f"⚠️ Retrying {func.__name__} due to: {type(e).__name__}: {str(e)[:100]}")
                raise
        return wrapper
    return decorator


def retry_file_operation(
    max_attempts: int = 3,
    initial_wait: float = 0.5,
    max_wait: float = 2.0
):
    """
    Retry decorator for file operations.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=initial_wait, max=max_wait),
            retry=retry_if_exception_type((IOError, OSError, PermissionError)),
            reraise=True
        )
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"⚠️ Retrying file operation {func.__name__} due to: {type(e).__name__}")
                raise
        return wrapper
    return decorator


# ==================== Simple Circuit Breaker ====================

class CircuitBreaker:
    """
    Simple circuit breaker pattern implementation.
    Opens circuit after failure_threshold failures within timeout seconds.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - (self.last_failure_time or 0) > self.timeout:
                self.state = "half_open"
                print(f"🔄 Circuit breaker half-open for {func.__name__}")
            else:
                raise Exception(f"Circuit breaker is OPEN for {func.__name__}. Too many failures.")
        
        try:
            result = func(*args, **kwargs)
            # Success - reset failure count
            if self.state == "half_open":
                self.state = "closed"
                print(f"✅ Circuit breaker closed for {func.__name__}")
            self.failure_count = 0
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                print(f"🔴 Circuit breaker OPENED for {func.__name__} after {self.failure_count} failures")
            
            raise
    
    def reset(self):
        """Manually reset circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"


# Global circuit breaker for OpenAI API calls
openai_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60.0,
    expected_exception=Exception
)


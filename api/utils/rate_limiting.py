"""
Rate Limiting Utilities for FastAPI Endpoints

Provides rate limiting decorators and middleware for expensive operations
like ML analytics, database dumps, and resource-intensive queries.

Security Focus: Prevent DoS attacks on computationally expensive endpoints.
"""

import logging
import time
from typing import Dict, Optional, Callable, Any
from functools import wraps
from datetime import datetime, timedelta

from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter for expensive operations.

    Tracks request counts per user/key and enforces limits.
    For production, consider using slowapi or Redis-backed implementation.
    """

    def __init__(self):
        """Initialize rate limiter with empty tracking dictionary."""
        self._requests: Dict[str, list] = {}

    def is_allowed(
        self,
        key: str,
        max_requests: int = 5,
        window_seconds: int = 60,
    ) -> bool:
        """
        Check if a request is allowed based on rate limit.

        Args:
            key: Unique identifier (e.g., user_id or IP address)
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        cutoff = now - window_seconds

        # Initialize or get request list for this key
        if key not in self._requests:
            self._requests[key] = []

        # Remove old requests outside the window
        self._requests[key] = [
            req_time for req_time in self._requests[key]
            if req_time > cutoff
        ]

        # Check if under limit
        if len(self._requests[key]) < max_requests:
            self._requests[key].append(now)
            return True

        return False

    def get_remaining(
        self,
        key: str,
        max_requests: int = 5,
        window_seconds: int = 60,
    ) -> int:
        """
        Get remaining requests for a key in current window.

        Args:
            key: Unique identifier
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Number of remaining requests (0 if rate limited)
        """
        now = time.time()
        cutoff = now - window_seconds

        if key not in self._requests:
            return max_requests

        # Count requests in window
        recent = [
            req_time for req_time in self._requests[key]
            if req_time > cutoff
        ]

        return max(0, max_requests - len(recent))

    def get_reset_time(
        self,
        key: str,
        window_seconds: int = 60,
    ) -> Optional[datetime]:
        """
        Get time when rate limit will be reset.

        Args:
            key: Unique identifier
            window_seconds: Time window in seconds

        Returns:
            datetime when oldest request falls out of window, or None
        """
        if key not in self._requests or not self._requests[key]:
            return None

        oldest = min(self._requests[key])
        reset_time = oldest + window_seconds
        return datetime.fromtimestamp(reset_time)


# Global rate limiter instance
_global_limiter = RateLimiter()


def rate_limit(
    max_requests: int = 5,
    window_seconds: int = 60,
    key_func: Optional[Callable[[Any], str]] = None,
) -> Callable:
    """
    Decorator to rate limit an endpoint.

    Usage:
        @router.get("/expensive-operation")
        @rate_limit(max_requests=5, window_seconds=60, key_func=lambda user: user.user_id)
        async def expensive_operation(user: CurrentUser):
            ...

    Args:
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds
        key_func: Function to extract rate limit key from request context
                 (default: uses anonymous key)

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract rate limit key
            if key_func:
                # Try to find a matching argument to pass to key_func
                key = None
                for arg in args:
                    if arg is not None:
                        key = key_func(arg)
                        if key:
                            break

                if not key:
                    for value in kwargs.values():
                        if value is not None:
                            key = key_func(value)
                            if key:
                                break

                if not key:
                    key = "anonymous"
            else:
                key = "anonymous"

            # Check rate limit
            if not _global_limiter.is_allowed(key, max_requests, window_seconds):
                remaining = _global_limiter.get_remaining(key, max_requests, window_seconds)
                reset_time = _global_limiter.get_reset_time(key, window_seconds)

                logger.warning(
                    "rate_limit_exceeded",
                    key=key,
                    max_requests=max_requests,
                    window_seconds=window_seconds,
                )

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds",
                        "remaining": remaining,
                        "reset_at": reset_time.isoformat() if reset_time else None,
                    },
                    headers={
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": str(remaining),
                        "X-RateLimit-Reset": str(int(reset_time.timestamp())) if reset_time else "0",
                    },
                )

            # Call the function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_user_id(user: Optional[Any]) -> Optional[str]:
    """
    Extract user ID from a User object.

    Args:
        user: User object with user_id attribute

    Returns:
        User ID string or None
    """
    if user is None:
        return None
    if hasattr(user, 'user_id'):
        return user.user_id
    return None


# Pre-configured rate limiters for common operations

ML_OPERATIONS_LIMITER = (5, 60)  # 5 requests per minute for ML operations
"""Rate limit for ML analytics: 5 operations per minute per user."""

DATABASE_DUMP_LIMITER = (2, 300)  # 2 requests per 5 minutes for database dumps
"""Rate limit for database exports: 2 operations per 5 minutes per user."""

SEARCH_LIMITER = (30, 60)  # 30 searches per minute per user
"""Rate limit for searches: 30 operations per minute per user."""

EXPORT_LIMITER = (10, 60)  # 10 exports per minute per user
"""Rate limit for exports: 10 operations per minute per user."""


class OperationTimedOut(Exception):
    """Exception raised when a long-running operation times out."""

    def __init__(self, operation: str, timeout_seconds: int):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        )


def with_timeout(timeout_seconds: int) -> Callable:
    """
    Decorator to enforce a timeout on async operations.

    Usage:
        @with_timeout(timeout_seconds=30)
        async def long_operation():
            ...

    Args:
        timeout_seconds: Maximum time to allow operation

    Returns:
        Decorator function
    """
    import asyncio

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                operation_name = func.__name__
                logger.warning(
                    "operation_timeout",
                    operation=operation_name,
                    timeout_seconds=timeout_seconds,
                )
                raise OperationTimedOut(operation_name, timeout_seconds)

        return wrapper

    return decorator

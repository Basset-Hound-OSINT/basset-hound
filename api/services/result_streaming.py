"""
Result Streaming Service for Basset Hound OSINT Platform.

Provides efficient handling of large result sets through:
- Chunked iteration for memory-efficient processing
- Async generators for streaming responses
- Pagination helpers for API endpoints
- Memory usage monitoring

Phase 20: Query & Performance Optimization
"""

import asyncio
import logging
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    TypeVar,
)

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# MODELS
# =============================================================================


class PaginationParams(BaseModel):
    """Parameters for paginated queries."""

    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=100, ge=1, le=1000, description="Max items to return")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")

    model_config = {"extra": "allow"}


class PaginatedResult(BaseModel, Generic[T]):
    """A paginated result set."""

    items: List[Any] = Field(default_factory=list, description="Current page items")
    total: int = Field(default=0, description="Total items across all pages")
    offset: int = Field(default=0, description="Current offset")
    limit: int = Field(default=100, description="Items per page")
    has_more: bool = Field(default=False, description="More items available")
    page: int = Field(default=1, description="Current page number (1-indexed)")
    total_pages: int = Field(default=1, description="Total number of pages")

    model_config = {"extra": "allow"}

    @classmethod
    def from_list(
        cls,
        items: List[Any],
        total: int,
        offset: int = 0,
        limit: int = 100,
    ) -> "PaginatedResult":
        """Create a paginated result from a list of items."""
        has_more = offset + len(items) < total
        page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        return cls(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more,
            page=page,
            total_pages=total_pages,
        )


class StreamingStats(BaseModel):
    """Statistics for streaming operations."""

    chunks_processed: int = 0
    items_processed: int = 0
    bytes_processed: int = 0
    processing_time_ms: float = 0.0
    peak_memory_mb: float = 0.0

    model_config = {"extra": "allow"}


# =============================================================================
# CHUNKED ITERATOR
# =============================================================================


class ChunkedIterator(Generic[T]):
    """
    Memory-efficient iterator that processes items in chunks.

    Instead of loading all items into memory, processes them in
    configurable chunk sizes.
    """

    def __init__(
        self,
        items: List[T],
        chunk_size: int = 100,
        transform: Optional[Callable[[T], T]] = None,
    ):
        """
        Initialize chunked iterator.

        Args:
            items: List of items to iterate
            chunk_size: Number of items per chunk
            transform: Optional transformation function for each item
        """
        self._items = items
        self._chunk_size = chunk_size
        self._transform = transform
        self._current_index = 0

    def __iter__(self) -> Iterator[List[T]]:
        """Iterate over chunks."""
        while self._current_index < len(self._items):
            end_index = min(self._current_index + self._chunk_size, len(self._items))
            chunk = self._items[self._current_index:end_index]

            if self._transform:
                chunk = [self._transform(item) for item in chunk]

            yield chunk
            self._current_index = end_index

    def reset(self) -> None:
        """Reset iterator to beginning."""
        self._current_index = 0

    @property
    def total_items(self) -> int:
        """Total number of items."""
        return len(self._items)

    @property
    def total_chunks(self) -> int:
        """Total number of chunks."""
        return (len(self._items) + self._chunk_size - 1) // self._chunk_size


# =============================================================================
# ASYNC STREAMING
# =============================================================================


class AsyncResultStream(Generic[T]):
    """
    Async generator for streaming large result sets.

    Enables memory-efficient streaming of query results
    without loading everything into memory.
    """

    def __init__(
        self,
        fetch_page: Callable[[int, int], List[T]],
        page_size: int = 100,
        max_items: Optional[int] = None,
    ):
        """
        Initialize async result stream.

        Args:
            fetch_page: Async function that takes (offset, limit) and returns items
            page_size: Number of items per page
            max_items: Maximum total items to stream (None for unlimited)
        """
        self._fetch_page = fetch_page
        self._page_size = page_size
        self._max_items = max_items
        self._stats = StreamingStats()

    async def stream(self) -> AsyncGenerator[T, None]:
        """
        Stream items one at a time.

        Yields:
            Individual items from the result set
        """
        offset = 0
        items_yielded = 0

        while True:
            # Respect max_items limit
            if self._max_items is not None and items_yielded >= self._max_items:
                break

            # Calculate how many items to fetch
            limit = self._page_size
            if self._max_items is not None:
                remaining = self._max_items - items_yielded
                limit = min(limit, remaining)

            # Fetch next page
            items = self._fetch_page(offset, limit)
            if not items:
                break

            self._stats.chunks_processed += 1

            # Yield items
            for item in items:
                if self._max_items is not None and items_yielded >= self._max_items:
                    break
                yield item
                items_yielded += 1
                self._stats.items_processed += 1

            # Check if we got fewer items than requested (end of data)
            if len(items) < limit:
                break

            offset += len(items)
            # Small delay to prevent overwhelming the database
            await asyncio.sleep(0.001)

    async def stream_chunks(self) -> AsyncGenerator[List[T], None]:
        """
        Stream items in chunks.

        Yields:
            Lists of items (chunks)
        """
        offset = 0
        items_streamed = 0

        while True:
            if self._max_items is not None and items_streamed >= self._max_items:
                break

            limit = self._page_size
            if self._max_items is not None:
                remaining = self._max_items - items_streamed
                limit = min(limit, remaining)

            items = self._fetch_page(offset, limit)
            if not items:
                break

            self._stats.chunks_processed += 1
            self._stats.items_processed += len(items)
            items_streamed += len(items)

            yield items

            if len(items) < limit:
                break

            offset += len(items)
            await asyncio.sleep(0.001)

    def get_stats(self) -> StreamingStats:
        """Get streaming statistics."""
        return self._stats.model_copy()


# =============================================================================
# PAGINATION UTILITIES
# =============================================================================


def paginate_list(
    items: List[T],
    offset: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
) -> PaginatedResult:
    """
    Paginate a list of items.

    Args:
        items: Full list of items
        offset: Number of items to skip
        limit: Maximum items to return
        sort_by: Optional attribute name to sort by
        sort_order: 'asc' or 'desc'

    Returns:
        PaginatedResult with the requested page
    """
    # Sort if requested
    if sort_by:
        reverse = sort_order == "desc"
        try:
            if isinstance(items[0], dict):
                items = sorted(items, key=lambda x: x.get(sort_by, ""), reverse=reverse)
            else:
                items = sorted(items, key=lambda x: getattr(x, sort_by, ""), reverse=reverse)
        except (IndexError, TypeError, KeyError):
            pass  # Keep original order if sorting fails

    total = len(items)
    page_items = items[offset:offset + limit]

    return PaginatedResult.from_list(
        items=page_items,
        total=total,
        offset=offset,
        limit=limit,
    )


def calculate_pagination(
    total: int,
    page: int = 1,
    per_page: int = 100,
) -> Dict[str, int]:
    """
    Calculate pagination parameters from page number.

    Args:
        total: Total number of items
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Dict with offset, limit, total_pages, has_prev, has_next
    """
    page = max(1, page)
    per_page = max(1, min(1000, per_page))

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    offset = (page - 1) * per_page

    return {
        "offset": offset,
        "limit": per_page,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


# =============================================================================
# MEMORY-EFFICIENT PROCESSING
# =============================================================================


async def process_in_batches(
    items: List[T],
    processor: Callable[[List[T]], Any],
    batch_size: int = 100,
    delay_between_batches: float = 0.01,
) -> List[Any]:
    """
    Process items in batches with optional delay between batches.

    Args:
        items: Items to process
        processor: Function to process each batch
        batch_size: Number of items per batch
        delay_between_batches: Delay in seconds between batches

    Returns:
        List of results from each batch
    """
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        result = processor(batch)
        if asyncio.iscoroutine(result):
            result = await result
        results.append(result)

        if delay_between_batches > 0 and i + batch_size < len(items):
            await asyncio.sleep(delay_between_batches)

    return results


def estimate_memory_usage(items: List[Any]) -> float:
    """
    Estimate memory usage of a list of items in MB.

    Note: This is a rough estimate, not exact measurement.

    Args:
        items: List of items to measure

    Returns:
        Estimated memory usage in MB
    """
    import sys

    try:
        # Get size of list structure
        total_size = sys.getsizeof(items)

        # Sample some items for estimation
        sample_size = min(100, len(items))
        if sample_size > 0:
            sample_items = items[:sample_size]
            sample_total = sum(sys.getsizeof(item) for item in sample_items)
            avg_item_size = sample_total / sample_size
            total_size += avg_item_size * len(items)

        return total_size / (1024 * 1024)  # Convert to MB
    except Exception:
        return 0.0


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "PaginationParams",
    "PaginatedResult",
    "StreamingStats",
    "ChunkedIterator",
    "AsyncResultStream",
    "paginate_list",
    "calculate_pagination",
    "process_in_batches",
    "estimate_memory_usage",
]

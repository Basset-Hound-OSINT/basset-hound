"""
Async HTTP client for Cletus news aggregation platform.

This module provides a robust client for consuming news event timelines
from Cletus, with proper error handling and graceful degradation.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("basset_hound.clients.cletus")


class CletusClient:
    """
    Async HTTP client for Cletus API.

    Provides methods for fetching event timelines, reports, and statistics
    from a Cletus instance running on a configurable host/port.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0):
        """
        Initialize the Cletus client.

        Args:
            base_url: Base URL for Cletus API. Defaults to CLETUS_BASE_URL env var
                     or http://localhost:9000.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url or os.getenv("CLETUS_BASE_URL", "http://localhost:9000")
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Create and configure the async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True
            )
            logger.info(f"Connected to Cletus at {self.base_url}")

    async def disconnect(self) -> None:
        """Close the HTTP client and release resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("Disconnected from Cletus")

    async def health_check(self) -> bool:
        """
        Check if Cletus is running and responding.

        Returns:
            bool: True if Cletus is healthy, False otherwise.
        """
        try:
            if not self.client:
                await self.connect()

            response = await self.client.get("/health")
            is_healthy = response.status_code == 200
            logger.debug(f"Cletus health check: {response.status_code}")
            return is_healthy
        except Exception as e:
            logger.warning(f"Cletus health check failed: {e}")
            return False

    async def list_events(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List event timelines from Cletus.

        Args:
            category: Filter by news category (optional).
            status: Filter by status (active, dormant, closed).
            severity: Filter by severity level.

        Returns:
            List of event timeline objects.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        if not self.client:
            await self.connect()

        params = {}
        if category:
            params["category"] = category
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity

        logger.debug(f"Listing events with params: {params}")
        response = await self.client.get("/api/events/", params=params)
        response.raise_for_status()
        events = response.json()
        logger.info(f"Retrieved {len(events)} events from Cletus")
        return events

    async def get_event(self, event_id: str) -> Dict[str, Any]:
        """
        Get a single event timeline by ID.

        Args:
            event_id: The event timeline ID.

        Returns:
            Event timeline object with all entries.

        Raises:
            httpx.HTTPError: If the request fails or event not found.
        """
        if not self.client:
            await self.connect()

        logger.debug(f"Fetching event: {event_id}")
        response = await self.client.get(f"/api/events/{event_id}")
        response.raise_for_status()
        return response.json()

    async def get_event_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics about all events in Cletus.

        Returns:
            Dictionary with statistics (total events, by category, etc).

        Raises:
            httpx.HTTPError: If the request fails.
        """
        if not self.client:
            await self.connect()

        logger.debug("Fetching event statistics")
        response = await self.client.get("/api/events/stats")
        response.raise_for_status()
        return response.json()

    async def search_events(self, query: str) -> List[Dict[str, Any]]:
        """
        Search events by title/summary.

        Args:
            query: Search query string.

        Returns:
            List of matching event timeline objects.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        if not self.client:
            await self.connect()

        logger.debug(f"Searching events: {query}")
        response = await self.client.get("/api/events/search", params={"q": query})
        response.raise_for_status()
        events = response.json()
        logger.info(f"Found {len(events)} matching events")
        return events

    async def list_reports(self) -> List[Dict[str, Any]]:
        """
        List all report sessions.

        Returns:
            List of report session objects.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        if not self.client:
            await self.connect()

        logger.debug("Listing report sessions")
        response = await self.client.get("/api/reports/sessions")
        response.raise_for_status()
        reports = response.json()
        logger.info(f"Retrieved {len(reports)} report sessions")
        return reports

    async def get_report(self, report_id: str) -> str:
        """
        Get full report content in markdown format.

        Args:
            report_id: The report session ID.

        Returns:
            Markdown content of the report.

        Raises:
            httpx.HTTPError: If the request fails or report not found.
        """
        if not self.client:
            await self.connect()

        logger.debug(f"Fetching report: {report_id}")
        response = await self.client.get(f"/api/reports/{report_id}")
        response.raise_for_status()
        return response.text

    async def export_articles_json(
        self,
        category: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Export articles as JSON.

        Args:
            category: Optional category filter.
            limit: Maximum number of articles to export.

        Returns:
            List of article objects.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        if not self.client:
            await self.connect()

        params = {"limit": limit}
        if category:
            params["category"] = category

        logger.debug(f"Exporting articles with params: {params}")
        response = await self.client.get("/api/export/articles/json", params=params)
        response.raise_for_status()
        articles = response.json()
        logger.info(f"Exported {len(articles)} articles")
        return articles


@asynccontextmanager
async def get_cletus_client(base_url: Optional[str] = None):
    """
    Context manager for Cletus client lifecycle.

    Handles connection and disconnection automatically.

    Args:
        base_url: Optional override for Cletus base URL.

    Yields:
        CletusClient instance or None if connection fails.

    Example:
        async with get_cletus_client() as client:
            events = await client.list_events()
    """
    client = CletusClient(base_url=base_url)
    try:
        await client.connect()
        yield client
    except Exception as e:
        logger.error(f"Failed to connect to Cletus: {e}")
        # Graceful degradation: yield None on connection failure
        yield None
    finally:
        await client.disconnect()

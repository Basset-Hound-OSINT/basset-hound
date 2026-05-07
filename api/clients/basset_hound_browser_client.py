"""
WebSocket Client for basset-hound-browser Electron Application.

This module provides an async WebSocket client to communicate with the
basset-hound-browser Electron app which runs a WebSocket server on port 8765.

Features:
- Async WebSocket connection management
- Request/response matching via request IDs
- Health checks and connection monitoring
- Command wrappers for common operations (navigate, screenshot, extract, etc.)
- Graceful degradation (returns None on connection failures)
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)


class BrowserClient:
    """
    Async WebSocket client for basset-hound-browser.

    Manages connection lifecycle, request/response matching, and provides
    high-level command methods for browser automation.
    """

    def __init__(
        self,
        ws_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 10.0,
        auto_reconnect: bool = False,
    ):
        """
        Initialize the browser client.

        Args:
            ws_url: WebSocket URL (defaults to BASSET_BROWSER_WS_URL env var or ws://localhost:8765)
            token: Authentication token (defaults to BASSET_BROWSER_WS_TOKEN env var)
            timeout: Request timeout in seconds
            auto_reconnect: Attempt to reconnect on disconnect (not used in this impl)
        """
        self.ws_url = ws_url or os.getenv(
            "BASSET_BROWSER_WS_URL", "ws://localhost:8765"
        )
        self.token = token or os.getenv("BASSET_BROWSER_WS_TOKEN")
        self.timeout = timeout
        self.websocket: Optional[ClientConnection] = None
        self._request_id_counter = 0
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._listener_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """
        Connect to browser WebSocket server.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            logger.info(f"Connecting to browser at {self.ws_url}...")
            self.websocket = await websockets.connect(
                self.ws_url, extra_headers=headers, ping_interval=20
            )

            # Start listener task to handle incoming messages
            self._listener_task = asyncio.create_task(self._listen())

            # Receive initial status frame
            try:
                status_msg = await asyncio.wait_for(
                    self.websocket.recv(), timeout=5.0
                )
                status = json.loads(status_msg)
                logger.info(f"Browser connection status: {status}")

                # Authenticate if required
                if status.get("authRequired"):
                    if not self.token:
                        raise ConnectionError(
                            "Browser requires authentication but no token provided"
                        )
                    await self.send_command("authenticate", token=self.token)
            except asyncio.TimeoutError:
                logger.warning(
                    "Timeout waiting for initial status frame (may be normal)"
                )

            logger.info("Browser client connected successfully")
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to browser at {self.ws_url}: {e}"
            )

    async def disconnect(self) -> None:
        """Close WebSocket connection and cleanup."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Browser client disconnected")

    async def _listen(self) -> None:
        """
        Background listener task for incoming WebSocket messages.

        Routes responses to pending requests via futures.
        """
        try:
            while self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(), timeout=self.timeout + 5
                    )
                    response = json.loads(message)

                    # Route to pending request
                    request_id = response.get("id")
                    if request_id and request_id in self._pending_responses:
                        future = self._pending_responses.pop(request_id)
                        if not future.done():
                            future.set_result(response)
                    else:
                        logger.debug(f"Received unmatched response: {response}")
                except asyncio.TimeoutError:
                    logger.debug("Listener timeout (no messages)")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to decode message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Listener error: {e}")

    async def send_command(self, command: str, **params) -> Dict[str, Any]:
        """
        Send a command and wait for response.

        Args:
            command: Command name
            **params: Command parameters

        Returns:
            Response dict from browser

        Raises:
            RuntimeError: If not connected
            asyncio.TimeoutError: If response times out
        """
        if not self.websocket:
            raise RuntimeError(
                "Not connected to browser. Call connect() first."
            )

        request_id = self._get_request_id()
        message = {"command": command, "id": request_id, **params}

        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self._pending_responses[request_id] = future

        try:
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent command {request_id}: {command}")

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=self.timeout)
            return response
        except asyncio.TimeoutError:
            self._pending_responses.pop(request_id, None)
            logger.error(f"Timeout waiting for response to command: {command}")
            raise
        except Exception as e:
            self._pending_responses.pop(request_id, None)
            logger.error(f"Error sending command {command}: {e}")
            raise

    def _get_request_id(self) -> str:
        """Generate unique request ID."""
        self._request_id_counter += 1
        return f"req_{self._request_id_counter}"

    # =========================================================================
    # High-level Command Wrappers
    # =========================================================================

    async def health_check(self) -> bool:
        """
        Check if browser is responsive.

        Returns:
            True if browser responds, False otherwise
        """
        try:
            result = await asyncio.wait_for(
                self.send_command("ping"), timeout=5.0
            )
            return result.get("success", False)
        except (
            ConnectionError,
            asyncio.TimeoutError,
            RuntimeError,
            Exception,
        ):
            return False

    async def status(self) -> Dict[str, Any]:
        """
        Get browser status.

        Returns:
            Status dict with connection info, active tabs, etc.
        """
        return await self.send_command("status")

    async def navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to URL.

        Args:
            url: URL to navigate to

        Returns:
            Response dict with success status
        """
        return await self.send_command("navigate", url=url)

    async def get_url(self) -> Optional[str]:
        """
        Get current page URL.

        Returns:
            Current URL or None
        """
        try:
            result = await self.send_command("get_url")
            return result.get("url")
        except Exception as e:
            logger.error(f"Failed to get URL: {e}")
            return None

    async def screenshot(self, full_page: bool = False) -> Optional[str]:
        """
        Take screenshot, return base64 string.

        Args:
            full_page: If True, capture full page; else viewport

        Returns:
            Base64-encoded image data or None
        """
        try:
            command = (
                "screenshot_full_page" if full_page else "screenshot"
            )
            result = await self.send_command(command)
            return result.get("data")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None

    async def extract_all(self) -> Dict[str, Any]:
        """
        Extract all content from page (text, HTML, metadata).

        Returns:
            Dict with extracted content
        """
        return await self.send_command("extract_all")

    async def get_page_state(self) -> Dict[str, Any]:
        """
        Get full page state (DOM, storage, etc.).

        Returns:
            Dict with page state
        """
        return await self.send_command("get_page_state")

    async def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """
        Fill form field.

        Args:
            selector: CSS selector or XPath
            value: Value to fill

        Returns:
            Response dict
        """
        return await self.send_command("fill", selector=selector, value=value)

    async def click(self, selector: str) -> Dict[str, Any]:
        """
        Click element.

        Args:
            selector: CSS selector or XPath

        Returns:
            Response dict
        """
        return await self.send_command("click", selector=selector)

    async def scroll(
        self, direction: str = "down", amount: int = 3
    ) -> Dict[str, Any]:
        """
        Scroll page.

        Args:
            direction: 'up' or 'down'
            amount: Number of scroll events

        Returns:
            Response dict
        """
        return await self.send_command(
            "scroll", direction=direction, amount=amount
        )

    async def wait_for_selector(
        self, selector: str, timeout: int = 5000
    ) -> Dict[str, Any]:
        """
        Wait for element to appear.

        Args:
            selector: CSS selector or XPath
            timeout: Timeout in milliseconds

        Returns:
            Response dict
        """
        return await self.send_command(
            "wait_for_selector", selector=selector, timeout=timeout
        )

    async def list_sessions(self) -> list:
        """
        List active browser sessions.

        Returns:
            List of session dicts
        """
        try:
            result = await self.send_command("list_sessions")
            return result.get("sessions", [])
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    async def create_session(self, name: str) -> Dict[str, Any]:
        """
        Create new browser session.

        Args:
            name: Session name

        Returns:
            Response dict with session info
        """
        return await self.send_command("create_session", name=name)

    async def switch_session(self, session_id: str) -> Dict[str, Any]:
        """
        Switch to session.

        Args:
            session_id: Session ID

        Returns:
            Response dict
        """
        return await self.send_command("switch_session", session_id=session_id)

    async def get_network_logs(self) -> list:
        """
        Get network request logs (for HAR export).

        Returns:
            List of network request dicts
        """
        try:
            result = await self.send_command("get_network_logs")
            return result.get("logs", [])
        except Exception as e:
            logger.error(f"Failed to get network logs: {e}")
            return []

    async def execute_script(self, script: str) -> Dict[str, Any]:
        """
        Execute arbitrary JavaScript.

        Args:
            script: JavaScript code to execute

        Returns:
            Response dict with execution result
        """
        return await self.send_command("execute_script", script=script)

    async def get_cookies(self) -> Dict[str, Any]:
        """
        Get all cookies for current page.

        Returns:
            Response dict with cookies
        """
        return await self.send_command("get_cookies")

    async def set_cookies(self, cookies: list) -> Dict[str, Any]:
        """
        Set cookies.

        Args:
            cookies: List of cookie dicts

        Returns:
            Response dict
        """
        return await self.send_command("set_cookies", cookies=cookies)


@asynccontextmanager
async def get_browser_client(
    ws_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: float = 10.0,
):
    """
    Context manager for browser client connection.

    Handles connection and cleanup. Returns None if connection fails,
    enabling graceful degradation.

    Example:
        async with get_browser_client() as client:
            if client:
                result = await client.navigate("https://example.com")
            else:
                # Browser not available, handle gracefully
                pass
    """
    client = BrowserClient(ws_url=ws_url, token=token, timeout=timeout)
    try:
        await client.connect()
        yield client
    except ConnectionError as e:
        logger.warning(f"Browser connection failed: {e}")
        # Graceful degradation: return None if browser not available
        yield None
    finally:
        try:
            await client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

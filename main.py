#!/usr/bin/env python3
"""
Basset Hound - Unified Entry Point

This script starts both the FastAPI server and MCP server concurrently.
Run with: python main.py

Prerequisites:
- Docker containers running (docker-compose up -d)
- Python dependencies installed (pip install -r requirements.txt)
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("basset_hound")


class ServiceManager:
    """Manages the lifecycle of Basset Hound services."""

    def __init__(self):
        self.mcp_process = None
        self.uvicorn_server = None
        self.shutdown_event = threading.Event()

    def start_mcp_server(self):
        """Start the MCP server in a subprocess."""
        logger.info("Starting MCP server...")

        mcp_server_path = Path(__file__).parent / "mcp" / "server.py"

        if not mcp_server_path.exists():
            logger.warning(f"MCP server not found at {mcp_server_path}")
            return None

        try:
            self.mcp_process = subprocess.Popen(
                [sys.executable, str(mcp_server_path)],
                env={**os.environ},
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            # Start a thread to log MCP output
            def log_mcp_output():
                for line in iter(self.mcp_process.stdout.readline, b''):
                    if self.shutdown_event.is_set():
                        break
                    logger.info(f"[MCP] {line.decode().strip()}")

            mcp_thread = threading.Thread(target=log_mcp_output, daemon=True)
            mcp_thread.start()

            logger.info(f"MCP server started (PID: {self.mcp_process.pid})")
            return self.mcp_process

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return None

    def stop_mcp_server(self):
        """Stop the MCP server subprocess."""
        if self.mcp_process:
            logger.info("Stopping MCP server...")
            self.mcp_process.terminate()
            try:
                self.mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.mcp_process.kill()
            logger.info("MCP server stopped")

    def run_fastapi_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the FastAPI server."""
        logger.info(f"Starting FastAPI server on {host}:{port}...")

        config = uvicorn.Config(
            "api.main:app",
            host=host,
            port=port,
            reload=os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
            log_level="info",
        )

        self.uvicorn_server = uvicorn.Server(config)
        return self.uvicorn_server

    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown handler."""
        logger.info("Initiating graceful shutdown...")
        self.shutdown_event.set()

        # Stop MCP server
        self.stop_mcp_server()

        # Stop uvicorn
        if self.uvicorn_server:
            self.uvicorn_server.should_exit = True

        logger.info("Shutdown complete")


def print_banner():
    """Print the application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗  █████╗ ███████╗███████╗███████╗████████╗           ║
    ║   ██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚══██╔══╝           ║
    ║   ██████╔╝███████║███████╗███████╗█████╗     ██║              ║
    ║   ██╔══██╗██╔══██║╚════██║╚════██║██╔══╝     ██║              ║
    ║   ██████╔╝██║  ██║███████║███████║███████╗   ██║              ║
    ║   ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝   ╚═╝              ║
    ║                                                               ║
    ║   ██╗  ██╗ ██████╗ ██╗   ██╗███╗   ██╗██████╗                 ║
    ║   ██║  ██║██╔═══██╗██║   ██║████╗  ██║██╔══██╗                ║
    ║   ███████║██║   ██║██║   ██║██╔██╗ ██║██║  ██║                ║
    ║   ██╔══██║██║   ██║██║   ██║██║╚██╗██║██║  ██║                ║
    ║   ██║  ██║╚██████╔╝╚██████╔╝██║ ╚████║██████╔╝                ║
    ║   ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═════╝                 ║
    ║                                                               ║
    ║   OSINT Investigation Platform                                ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_startup_info(host: str, port: int, mcp_enabled: bool):
    """Print startup information."""
    print("\n" + "=" * 60)
    print("  Basset Hound is running!")
    print("=" * 60)
    print(f"\n  FastAPI Server:")
    print(f"    - API:      http://{host}:{port}")
    print(f"    - Docs:     http://{host}:{port}/docs")
    print(f"    - ReDoc:    http://{host}:{port}/redoc")
    print(f"    - Health:   http://{host}:{port}/health")
    print(f"\n  MCP Server:")
    if mcp_enabled:
        print(f"    - Status:   Running (stdio mode)")
        print(f"    - Tools:    15 entity management tools available")
    else:
        print(f"    - Status:   Not started")
    print(f"\n  Authentication:")
    auth_enabled = os.getenv("AUTH_ENABLED", "false").lower() in ("true", "1", "yes")
    print(f"    - Status:   {'Enabled' if auth_enabled else 'Disabled (development mode)'}")
    print("\n" + "=" * 60)
    print("  Press Ctrl+C to stop all services")
    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Basset Hound OSINT Platform")
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Don't start the MCP server"
    )
    parser.add_argument(
        "--mcp-only",
        action="store_true",
        help="Only start the MCP server (no FastAPI)"
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    # Create service manager
    manager = ServiceManager()

    # Register signal handlers
    signal.signal(signal.SIGINT, manager.shutdown)
    signal.signal(signal.SIGTERM, manager.shutdown)

    # Start MCP server if requested
    mcp_enabled = False
    if not args.no_mcp:
        mcp_process = manager.start_mcp_server()
        mcp_enabled = mcp_process is not None

    # If MCP-only mode, just wait for the MCP process
    if args.mcp_only:
        if manager.mcp_process:
            print_startup_info(args.host, args.port, mcp_enabled)
            try:
                manager.mcp_process.wait()
            except KeyboardInterrupt:
                manager.shutdown()
        else:
            logger.error("MCP server failed to start")
            sys.exit(1)
        return

    # Start FastAPI server
    print_startup_info(args.host, args.port, mcp_enabled)

    try:
        server = manager.run_fastapi_server(args.host, args.port)
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        manager.shutdown()


if __name__ == "__main__":
    main()

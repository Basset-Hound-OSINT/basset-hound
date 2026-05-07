"""
Structured Logging Configuration using structlog

This module configures JSON-based structured logging for the Basset Hound application.
It provides a centralized logger factory that returns structlog loggers configured
for JSON output with timestamps and log levels.
"""

import structlog


def configure_logging():
    """
    Configure structlog with JSON output and standard processors.

    This should be called once during application startup.
    Configures:
    - TimeStamper: ISO 8601 formatted timestamps
    - add_log_level: Includes log level in each message
    - JSONRenderer: Outputs JSON format for structured logs
    """
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """
    Get a structlog logger instance.

    Args:
        name: The name of the logger (typically __name__)

    Returns:
        A structlog logger instance
    """
    return structlog.get_logger(name)

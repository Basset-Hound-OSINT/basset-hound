"""
Basset Hound API Services

This module contains service classes for interacting with external systems
and databases. Services encapsulate business logic and data access patterns.
"""

from .neo4j_service import AsyncNeo4jService
from .auto_linker import AutoLinker, get_auto_linker

__all__ = ["AsyncNeo4jService", "AutoLinker", "get_auto_linker"]

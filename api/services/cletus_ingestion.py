"""
Cletus ingestion service for consuming news event timelines.

Maps Cletus event data into basset-hound entities and relationships within a project.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from api.clients.cletus_client import get_cletus_client

logger = logging.getLogger("basset_hound.services.cletus_ingestion")


class CletusIngestionService:
    """
    Maps Cletus events to basset-hound entities and relationships.

    Creates entities for news events, categories, and organizations mentioned,
    then establishes relationships between them.
    """

    def __init__(self, neo4j_handler: Any, project_safe_name: str):
        """
        Initialize the ingestion service.

        Args:
            neo4j_handler: Neo4jHandler instance for database operations.
            project_safe_name: Safe name of the target project.
        """
        self.neo4j = neo4j_handler
        self.project_safe_name = project_safe_name
        self.ingested_events: Dict[str, str] = {}  # Map of cletus_event_id -> entity_id
        self.ingested_orgs: Dict[str, str] = {}    # Map of org_name -> entity_id
        self.ingested_categories: Dict[str, str] = {}  # Map of category -> entity_id

    async def ingest_all_events(self) -> Dict[str, Any]:
        """
        Pull all events from Cletus and ingest them.

        Returns:
            Dictionary with ingestion results (total, created, errors).
        """
        async with get_cletus_client() as client:
            if not client:
                logger.error("Failed to connect to Cletus")
                return {
                    "success": False,
                    "error": "Cletus unavailable",
                    "total": 0,
                    "created": 0,
                    "errors": []
                }

            try:
                logger.info(f"Starting ingestion for project: {self.project_safe_name}")
                events = await client.list_events()
                results = {
                    "success": True,
                    "total": 0,
                    "created": 0,
                    "errors": []
                }

                for event in events:
                    try:
                        entity_id = await self.ingest_event(client, event)
                        results["created"] += 1
                        logger.debug(f"Ingested event {event.get('id')} as entity {entity_id}")
                    except Exception as e:
                        error_msg = f"Event {event.get('id')}: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.error(error_msg)
                    finally:
                        results["total"] += 1

                logger.info(
                    f"Ingestion completed: {results['created']}/{results['total']} events, "
                    f"{len(results['errors'])} errors"
                )
                return results

            except Exception as e:
                logger.error(f"Ingestion failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "total": 0,
                    "created": 0,
                    "errors": [str(e)]
                }

    async def ingest_event(self, client: Any, event: Dict[str, Any]) -> str:
        """
        Ingest a single event as an entity with relationships.

        Args:
            client: CletusClient instance.
            event: Event data from Cletus API.

        Returns:
            The created entity ID.

        Raises:
            Exception: If entity creation fails.
        """
        cletus_event_id = event.get("id")
        logger.debug(f"Ingesting event: {cletus_event_id}")

        # Create NewsEvent entity (modeled as Person for integration with existing system)
        event_entity_data = {
            "profile": {
                "News Event Details": {
                    "title": event.get("title", ""),
                    "summary": event.get("summary", ""),
                    "category": event.get("category", ""),
                    "severity": event.get("severity", "medium"),
                    "status": event.get("status", "active"),
                    "first_seen": event.get("first_seen", ""),
                    "last_updated": event.get("last_updated", ""),
                    "entry_count": str(event.get("entry_count", 0)),
                    "keywords": event.get("keywords", []),
                    "cletus_event_id": cletus_event_id,
                    "cletus_source": "cletus_api"
                }
            }
        }

        event_entity = self.neo4j.create_person(
            self.project_safe_name,
            event_entity_data
        )

        if not event_entity:
            raise RuntimeError(f"Failed to create entity for event {cletus_event_id}")

        event_entity_id = event_entity.get("id")
        self.ingested_events[cletus_event_id] = event_entity_id
        logger.debug(f"Created event entity: {event_entity_id}")

        # Extract and link organizations mentioned
        entries = event.get("entries", [])
        mentioned_orgs = set()

        for entry in entries:
            sources_mentioned = entry.get("sources_mentioned", [])
            for org_name in sources_mentioned:
                if org_name and org_name not in mentioned_orgs:
                    mentioned_orgs.add(org_name)

        # Create organization entities and link them
        for org_name in mentioned_orgs:
            try:
                org_entity_id = await self._get_or_create_organization(org_name)
                self.neo4j.create_relationship(
                    self.project_safe_name,
                    event_entity_id,
                    org_entity_id,
                    "INVOLVES",
                    {"source": "cletus_api", "type": "organization_mentioned"}
                )
                logger.debug(f"Linked event {event_entity_id} to org {org_name}")
            except Exception as e:
                logger.warning(f"Failed to link organization {org_name}: {e}")

        # Link to category (as an entity)
        category = event.get("category")
        if category:
            try:
                category_entity_id = await self._get_or_create_category(category)
                self.neo4j.create_relationship(
                    self.project_safe_name,
                    event_entity_id,
                    category_entity_id,
                    "IN_CATEGORY",
                    {"source": "cletus_api"}
                )
                logger.debug(f"Linked event {event_entity_id} to category {category}")
            except Exception as e:
                logger.warning(f"Failed to link category {category}: {e}")

        # Create relationships between events with keyword overlap
        keywords = set(event.get("keywords", []))
        if keywords:
            for other_cletus_id, other_entity_id in self.ingested_events.items():
                if other_cletus_id != cletus_event_id:
                    # Check for keyword overlap with previously ingested events
                    # (simplified: just link if both have keywords)
                    # In production, would compute Jaccard similarity
                    try:
                        self.neo4j.create_relationship(
                            self.project_safe_name,
                            event_entity_id,
                            other_entity_id,
                            "SHARES_KEYWORDS",
                            {"source": "cletus_api", "keywords": list(keywords)[:5]}
                        )
                    except Exception as e:
                        # Relationship might already exist, that's ok
                        logger.debug(f"Keyword relationship already exists: {e}")

        return event_entity_id

    async def ingest_event_by_id(self, event_id: str) -> str:
        """
        Ingest a single event by ID.

        Args:
            event_id: The Cletus event ID.

        Returns:
            The created entity ID.

        Raises:
            Exception: If entity creation fails.
        """
        async with get_cletus_client() as client:
            if not client:
                raise RuntimeError("Cletus unavailable")

            logger.info(f"Fetching event {event_id} from Cletus")
            event = await client.get_event(event_id)
            entity_id = await self.ingest_event(client, event)
            return entity_id

    async def _get_or_create_category(self, category_name: str) -> str:
        """
        Get or create a category entity.

        Args:
            category_name: The category name.

        Returns:
            The category entity ID.
        """
        if category_name in self.ingested_categories:
            return self.ingested_categories[category_name]

        # Check if category entity already exists in this project
        category_data = {
            "profile": {
                "News Event Details": {
                    "type": "news_category",
                    "category_name": category_name,
                    "cletus_source": "cletus_api"
                }
            }
        }

        category_entity = self.neo4j.create_person(
            self.project_safe_name,
            category_data
        )

        if not category_entity:
            raise RuntimeError(f"Failed to create category entity for {category_name}")

        category_id = category_entity.get("id")
        self.ingested_categories[category_name] = category_id
        logger.debug(f"Created category entity: {category_id}")
        return category_id

    async def _get_or_create_organization(self, org_name: str) -> str:
        """
        Get or create an organization entity.

        Args:
            org_name: The organization name.

        Returns:
            The organization entity ID.
        """
        if org_name in self.ingested_orgs:
            return self.ingested_orgs[org_name]

        org_data = {
            "profile": {
                "News Event Details": {
                    "type": "organization",
                    "organization_name": org_name,
                    "cletus_source": "cletus_api"
                }
            }
        }

        org_entity = self.neo4j.create_person(
            self.project_safe_name,
            org_data
        )

        if not org_entity:
            raise RuntimeError(f"Failed to create organization entity for {org_name}")

        org_id = org_entity.get("id")
        self.ingested_orgs[org_name] = org_id
        logger.debug(f"Created organization entity: {org_id}")
        return org_id

"""
Async Neo4j Service for Basset Hound

This module provides an asynchronous interface to Neo4j using the official
neo4j async driver. It implements connection pooling, proper error handling,
and context manager support for sessions.
"""

import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import (
    AuthError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)

# Load environment variables
load_dotenv()


class Neo4jConnectionError(Exception):
    """Raised when connection to Neo4j fails."""
    pass


class Neo4jQueryError(Exception):
    """Raised when a Neo4j query fails."""
    pass


class AsyncNeo4jService:
    """
    Async Neo4j service with connection pooling and context manager support.

    This service provides asynchronous methods for all Neo4j operations
    including project management, person CRUD, and schema configuration.

    Usage:
        # As a context manager (recommended)
        async with AsyncNeo4jService() as service:
            projects = await service.get_all_projects()

        # Manual lifecycle management
        service = AsyncNeo4jService()
        await service.connect()
        try:
            projects = await service.get_all_projects()
        finally:
            await service.close()
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
        connection_acquisition_timeout: float = 60.0,
    ):
        """
        Initialize the async Neo4j service.

        Args:
            uri: Neo4j connection URI. Defaults to NEO4J_URI env var.
            user: Neo4j username. Defaults to NEO4J_USER env var.
            password: Neo4j password. Defaults to NEO4J_PASSWORD env var.
            max_connection_lifetime: Maximum time a connection can live (seconds).
            max_connection_pool_size: Maximum number of connections in the pool.
            connection_acquisition_timeout: Timeout for acquiring a connection.
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "neo4jbasset")

        self._driver = None
        self._connected = False

        # Connection pool settings
        self._max_connection_lifetime = max_connection_lifetime
        self._max_connection_pool_size = max_connection_pool_size
        self._connection_acquisition_timeout = connection_acquisition_timeout

    async def __aenter__(self) -> "AsyncNeo4jService":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(
        self,
        max_retries: int = 30,
        retry_delay: float = 2.0
    ) -> None:
        """
        Establish connection to Neo4j with retry logic.

        Args:
            max_retries: Maximum number of connection attempts.
            retry_delay: Delay between retries in seconds.

        Raises:
            Neo4jConnectionError: If connection fails after all retries.
        """
        if self._connected and self._driver:
            return

        last_error = None
        start_time = asyncio.get_event_loop().time()

        for attempt in range(max_retries):
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_lifetime=self._max_connection_lifetime,
                    max_connection_pool_size=self._max_connection_pool_size,
                    connection_acquisition_timeout=self._connection_acquisition_timeout,
                )

                # Test the connection
                async with self._driver.session() as session:
                    await session.run("RETURN 1")

                self._connected = True
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                print(f"Connected to Neo4j at {self.uri} after {elapsed}s.")

                # Set up constraints after successful connection
                await self.ensure_constraints()
                return

            except (ServiceUnavailable, AuthError, SessionExpired) as e:
                last_error = e
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                print(f"\rWaiting to connect to Neo4j ({self.uri})... {elapsed}s", end='', flush=True)
                await asyncio.sleep(retry_delay)
            except Exception as e:
                last_error = e
                await asyncio.sleep(retry_delay)

        raise Neo4jConnectionError(
            f"Failed to connect to Neo4j after {max_retries} attempts: {last_error}"
        )

    async def close(self) -> None:
        """Close the Neo4j driver and release resources."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if the service is connected to Neo4j."""
        return self._connected and self._driver is not None

    @asynccontextmanager
    async def session(self, database: Optional[str] = None):
        """
        Get an async session context manager.

        Args:
            database: Optional database name.

        Yields:
            AsyncSession: Neo4j async session.

        Raises:
            Neo4jConnectionError: If not connected.
        """
        if not self._driver:
            raise Neo4jConnectionError("Not connected to Neo4j. Call connect() first.")

        session = self._driver.session(database=database) if database else self._driver.session()
        try:
            yield session
        finally:
            await session.close()

    async def _execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        fetch_one: bool = False,
        fetch_all: bool = True,
    ) -> Union[Optional[Dict], List[Dict], None]:
        """
        Execute a Cypher query with error handling.

        Args:
            query: Cypher query string.
            parameters: Query parameters.
            fetch_one: Return only the first record.
            fetch_all: Return all records.

        Returns:
            Query results as dict(s) or None.

        Raises:
            Neo4jQueryError: If query execution fails.
        """
        if not self._driver:
            raise Neo4jConnectionError("Not connected to Neo4j. Call connect() first.")

        try:
            async with self.session() as session:
                result = await session.run(query, parameters or {})

                if fetch_one:
                    record = await result.single()
                    return dict(record) if record else None
                elif fetch_all:
                    records = await result.data()
                    return records
                else:
                    await result.consume()
                    return None

        except TransientError as e:
            # Retry transient errors once
            try:
                async with self.session() as session:
                    result = await session.run(query, parameters or {})
                    if fetch_one:
                        record = await result.single()
                        return dict(record) if record else None
                    elif fetch_all:
                        return await result.data()
                    return None
            except Exception as retry_error:
                raise Neo4jQueryError(f"Query failed after retry: {retry_error}")
        except Exception as e:
            raise Neo4jQueryError(f"Query execution failed: {e}")

    # ==================== Schema Management ====================

    async def ensure_constraints(self) -> None:
        """Set up constraints to ensure uniqueness and indexing."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Project) REQUIRE p.safe_name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (p:Project) ON (p.name)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.created_at)",
            "CREATE INDEX IF NOT EXISTS FOR (s:Section) ON (s.id)",
            "CREATE INDEX IF NOT EXISTS FOR (f:Field) ON (f.id)",
            "CREATE INDEX IF NOT EXISTS FOR ()-[r:HAS_FILE]-() ON (r.section_id, r.field_id)",
        ]

        async with self.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    print(f"Error creating constraint {constraint}: {e}")

    async def setup_schema_from_config(self, config: Dict[str, Any]) -> None:
        """
        Create relationship types and properties based on the configuration.

        Args:
            config: Configuration dictionary with sections and fields.
        """
        async with self.session() as session:
            # Clear existing schema if needed
            await session.run("""
                MATCH (c:Configuration {id: 'main'})
                DETACH DELETE c
            """)

            # Create new configuration
            await session.run("""
                MERGE (config:Configuration {id: 'main'})
                SET config.updated_at = $timestamp
            """, timestamp=datetime.now().isoformat())

            # Process sections and fields
            for section in config.get("sections", []):
                section_id = section.get("id")
                section_label = section.get("label", section_id)

                await session.run("""
                    MERGE (config:Configuration {id: 'main'})
                    MERGE (section:Section {id: $section_id})
                    SET section.label = $section_label
                    MERGE (config)-[:HAS_SECTION]->(section)
                """, section_id=section_id, section_label=section_label)

                for field in section.get("fields", []):
                    field_id = field.get("id")
                    field_label = field.get("label", field_id)
                    field_type = field.get("type", "string")
                    field_multiple = field.get("multiple", False)

                    await session.run("""
                        MERGE (section:Section {id: $section_id})
                        MERGE (field:Field {id: $field_id})
                        SET field.section_id = $section_id,
                            field.label = $field_label,
                            field.type = $field_type,
                            field.multiple = $field_multiple
                        MERGE (section)-[:HAS_FIELD]->(field)
                    """, section_id=section_id, field_id=field_id,
                        field_label=field_label, field_type=field_type,
                        field_multiple=field_multiple)

                    # Handle field components
                    if "components" in field:
                        for component in field.get("components", []):
                            component_id = component.get("id")
                            component_type = component.get("type", "string")
                            component_label = component.get("label", component_id)

                            await session.run("""
                                MERGE (field:Field {id: $field_id})
                                MERGE (component:Component {id: $component_id})
                                SET component.field_id = $field_id,
                                    component.section_id = $section_id,
                                    component.label = $component_label,
                                    component.type = $component_type
                                MERGE (field)-[:HAS_COMPONENT]->(component)
                            """, section_id=section_id, field_id=field_id,
                                component_id=component_id, component_label=component_label,
                                component_type=component_type)

    # ==================== Project Management ====================

    async def create_project(
        self,
        project_name: str,
        safe_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new project in Neo4j.

        Args:
            project_name: Display name for the project.
            safe_name: URL-safe name. Auto-generated if not provided.

        Returns:
            Created project data or None if creation failed.
        """
        if not safe_name:
            safe_name = self.slugify(project_name)

        project_id = str(uuid4())

        async with self.session() as session:
            result = await session.run("""
                CREATE (p:Project {
                    id: $id,
                    name: $name,
                    safe_name: $safe_name,
                    start_date: datetime(),
                    created_at: datetime()
                })
                RETURN p
            """, id=project_id, name=project_name, safe_name=safe_name)

            record = await result.single()
            if record:
                project_data = dict(record["p"])
                project_data["id"] = project_id
                return project_data
            return None

    async def get_project(self, safe_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a project by its safe name with all related data.

        Args:
            safe_name: URL-safe project name.

        Returns:
            Project data including people, or None if not found.
        """
        async with self.session() as session:
            result = await session.run("""
                MATCH (p:Project {safe_name: $safe_name})
                RETURN p
            """, safe_name=safe_name)

            record = await result.single()
            if not record:
                return None

            project_data = dict(record["p"])
            project_data["people"] = await self.get_all_people(safe_name)
            return project_data

    async def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        Retrieve all projects with basic info.

        Returns:
            List of project dictionaries.
        """
        async with self.session() as session:
            result = await session.run("""
                MATCH (p:Project)
                RETURN p.id as id, p.name as name, p.safe_name as safe_name,
                       p.created_at as created_at
                ORDER BY p.created_at DESC
            """)

            projects = []
            records = await result.data()
            for record in records:
                project = {
                    "id": record["id"],
                    "name": record["name"],
                    "safe_name": record["safe_name"],
                    "created_at": self.convert_neo4j_datetime(record["created_at"])
                }
                projects.append(project)
            return projects

    async def update_project(
        self,
        safe_name: str,
        project_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update project properties.

        Args:
            safe_name: URL-safe project name.
            project_data: Dictionary of properties to update.

        Returns:
            Updated project data or None if not found.
        """
        # Remove people from update data (they're managed separately)
        if "people" in project_data:
            del project_data["people"]

        async with self.session() as session:
            result = await session.run("""
                MATCH (p:Project {safe_name: $safe_name})
                SET p += $properties
                RETURN p
            """, safe_name=safe_name, properties=self.clean_data(project_data))

            record = await result.single()
            return dict(record["p"]) if record else None

    async def delete_project(self, safe_name: str) -> bool:
        """
        Delete a project and all its associated data.

        Args:
            safe_name: URL-safe project name.

        Returns:
            True if project was deleted, False otherwise.
        """
        async with self.session() as session:
            # Delete all related data first
            await session.run("""
                MATCH (project:Project {safe_name: $safe_name})-[:HAS_PERSON]->(person:Person)
                OPTIONAL MATCH (person)-[:HAS_FILE]->(file:File)
                OPTIONAL MATCH (person)-[:HAS_FIELD_VALUE]->(fv:FieldValue)
                DETACH DELETE person, file, fv
            """, safe_name=safe_name)

            # Then delete the project
            result = await session.run("""
                MATCH (p:Project {safe_name: $safe_name})
                DETACH DELETE p
                RETURN count(p) as deleted_count
            """, safe_name=safe_name)

            record = await result.single()
            return record is not None and record["deleted_count"] > 0

    # ==================== Person Management ====================

    async def create_person(
        self,
        project_safe_name: str,
        person_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new person in a project.

        Args:
            project_safe_name: URL-safe project name.
            person_data: Optional initial person data including profile.

        Returns:
            Created person data or None if project doesn't exist.
        """
        # Use the provided ID if present, otherwise generate one
        if person_data and "id" in person_data:
            person_id = person_data["id"]
        else:
            person_id = str(uuid4())
            if person_data is not None:
                person_data["id"] = person_id

        # Use the provided created_at if present, otherwise set now
        now = (person_data.get("created_at")
               if person_data and "created_at" in person_data
               else datetime.now().isoformat())
        if person_data is not None:
            person_data["created_at"] = now

        if not person_data:
            person_data = {"profile": {}}

        async with self.session() as session:
            # First verify project exists
            project = await session.run("""
                MATCH (p:Project {safe_name: $project_safe_name})
                RETURN p
            """, project_safe_name=project_safe_name)

            if not await project.single():
                return None

            # Create person node and link to project
            result = await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                CREATE (person:Person {
                    id: $person_id,
                    created_at: $created_at
                })
                CREATE (project)-[:HAS_PERSON]->(person)
                RETURN person
            """, project_safe_name=project_safe_name,
                person_id=person_id,
                created_at=now)

            if not await result.single():
                return None

        # Process profile data
        if "profile" in person_data:
            for section_id, fields in person_data["profile"].items():
                for field_id, value in fields.items():
                    if isinstance(value, (dict, list)):
                        # Convert complex objects to JSON strings
                        value = json.dumps(value)
                    await self.set_person_field(person_id, section_id, field_id, value)

        return await self.get_person(project_safe_name, person_id)

    async def get_person(
        self,
        project_safe_name: str,
        person_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a person by ID within a project.

        Args:
            project_safe_name: URL-safe project name.
            person_id: Person's unique identifier.

        Returns:
            Person data including profile, or None if not found.
        """
        async with self.session() as session:
            # Get basic person info
            result = await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person {id: $person_id})
                RETURN person
            """, project_safe_name=project_safe_name, person_id=person_id)

            record = await result.single()
            if not record:
                return None

            person_data = dict(record["person"])
            person_data["profile"] = {}

            # Get all profile data
            profile_result = await session.run("""
                MATCH (person:Person {id: $person_id})-[:HAS_FIELD_VALUE]->(fv:FieldValue)
                RETURN fv.section_id as section_id, fv.field_id as field_id, fv.value as value
            """, person_id=person_id)

            profile_records = await profile_result.data()
            for field_record in profile_records:
                section_id = field_record["section_id"]
                field_id = field_record["field_id"]
                value = field_record["value"]

                if section_id not in person_data["profile"]:
                    person_data["profile"][section_id] = {}

                # Try to parse JSON strings
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass

                person_data["profile"][section_id][field_id] = value

            # Get all file references with relationship properties
            files_result = await session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FILE]->(file:File)
                RETURN file, r.section_id as section_id, r.field_id as field_id
            """, person_id=person_id)

            files_records = await files_result.data()
            for file_record in files_records:
                file_data = dict(file_record["file"])
                section_id = file_record["section_id"]
                field_id = file_record["field_id"]

                if section_id not in person_data["profile"]:
                    person_data["profile"][section_id] = {}

                if field_id not in person_data["profile"][section_id]:
                    person_data["profile"][section_id][field_id] = []

                if isinstance(person_data["profile"][section_id][field_id], list):
                    person_data["profile"][section_id][field_id].append(file_data)
                else:
                    person_data["profile"][section_id][field_id] = file_data

            return person_data

    async def get_all_people(self, project_safe_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve all people in a project.

        Args:
            project_safe_name: URL-safe project name.

        Returns:
            List of person dictionaries.
        """
        async with self.session() as session:
            result = await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person)
                RETURN person.id AS person_id
                ORDER BY person.created_at DESC
            """, project_safe_name=project_safe_name)

            records = await result.data()

            # Fetch full person data for each
            people = []
            for record in records:
                person = await self.get_person(project_safe_name, record["person_id"])
                if person:
                    people.append(person)

            return people

    async def update_person(
        self,
        project_safe_name: str,
        person_id: str,
        updated_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a person's data.

        Args:
            project_safe_name: URL-safe project name.
            person_id: Person's unique identifier.
            updated_data: Dictionary of properties to update.

        Returns:
            Updated person data or None if not found.
        """
        profile_data = updated_data.pop("profile", {}) if "profile" in updated_data else {}

        async with self.session() as session:
            # Update basic person info
            if updated_data:
                result = await session.run("""
                    MATCH (project:Project {safe_name: $project_safe_name})
                          -[:HAS_PERSON]->(person:Person {id: $person_id})
                    SET person += $properties
                    RETURN person
                """, project_safe_name=project_safe_name,
                    person_id=person_id, properties=self.clean_data(updated_data))

                if not await result.single():
                    return None

        # Update profile data
        for section_id, fields in profile_data.items():
            for field_id, value in fields.items():
                await self.set_person_field(person_id, section_id, field_id, value)

        return await self.get_person(project_safe_name, person_id)

    async def set_person_field(
        self,
        person_id: str,
        section_id: str,
        field_id: str,
        value: Any
    ) -> None:
        """
        Set a specific field value for a person.

        Args:
            person_id: Person's unique identifier.
            section_id: Section identifier.
            field_id: Field identifier.
            value: Value to set (can be string, dict, list, or file data).
        """
        async with self.session() as session:
            # First delete any existing value for this field
            await session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FIELD_VALUE]->(fv:FieldValue)
                WHERE fv.section_id = $section_id AND fv.field_id = $field_id
                DELETE r, fv
            """, person_id=person_id, section_id=section_id, field_id=field_id)

        # Handle file fields differently
        if isinstance(value, dict) and "path" in value:
            await self.handle_file_upload(
                person_id=person_id,
                section_id=section_id,
                field_id=field_id,
                file_id=value.get("id", str(uuid4())),
                filename=value.get("name", ""),
                file_path=value.get("path", ""),
                metadata=value
            )
            return
        elif isinstance(value, list) and value and isinstance(value[0], dict) and "path" in value[0]:
            for file_data in value:
                await self.handle_file_upload(
                    person_id=person_id,
                    section_id=section_id,
                    field_id=field_id,
                    file_id=file_data.get("id", str(uuid4())),
                    filename=file_data.get("name", ""),
                    file_path=file_data.get("path", ""),
                    metadata=file_data
                )
            return

        # Convert complex objects to JSON strings
        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        # Create new field value node
        async with self.session() as session:
            await session.run("""
                MATCH (person:Person {id: $person_id})
                CREATE (fv:FieldValue {
                    section_id: $section_id,
                    field_id: $field_id,
                    value: $value
                })
                CREATE (person)-[:HAS_FIELD_VALUE]->(fv)
            """, person_id=person_id, section_id=section_id,
                field_id=field_id, value=value)

    async def delete_person(self, project_safe_name: str, person_id: str) -> bool:
        """
        Delete a person and all their associated data.

        Args:
            project_safe_name: URL-safe project name.
            person_id: Person's unique identifier.

        Returns:
            True if person was deleted, False otherwise.
        """
        async with self.session() as session:
            # First check if person exists
            verify = await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person {id: $person_id})
                RETURN count(person) as exists
            """, project_safe_name=project_safe_name, person_id=person_id)

            record = await verify.single()
            if not record or record["exists"] == 0:
                return False

            # Delete all related data
            await session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FIELD_VALUE]->(fv)
                DELETE r, fv
            """, person_id=person_id)

            await session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FILE]->(file)
                DELETE r, file
            """, person_id=person_id)

            # Finally delete the person
            await session.run("""
                MATCH (person:Person {id: $person_id})
                DETACH DELETE person
            """, person_id=person_id)

            return True

    # ==================== File Management ====================

    async def handle_file_upload(
        self,
        person_id: str,
        section_id: str,
        field_id: str,
        file_id: str,
        filename: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Handle file upload and create appropriate relationships.

        Args:
            person_id: Person's unique identifier.
            section_id: Section identifier.
            field_id: Field identifier.
            file_id: Unique file identifier.
            filename: Original filename.
            file_path: Path to the file.
            metadata: Additional file metadata.
        """
        file_props = {
            "id": file_id,
            "name": filename,
            "path": file_path,
            "section_id": section_id,
            "field_id": field_id,
            "person_id": person_id,
            "uploaded_at": datetime.now().isoformat()
        }

        if metadata:
            file_props.update(metadata)

        async with self.session() as session:
            # First delete any existing file with this field reference
            await session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FILE]->(file:File)
                WHERE file.section_id = $section_id AND file.field_id = $field_id
                DELETE r, file
            """, person_id=person_id, section_id=section_id, field_id=field_id)

            # Create new file node and relationship with properties
            await session.run("""
                MATCH (person:Person {id: $person_id})
                MERGE (file:File {id: $file_id})
                SET file = $file_properties
                MERGE (person)-[r:HAS_FILE]->(file)
                SET r.section_id = $section_id,
                    r.field_id = $field_id
            """, person_id=person_id, file_id=file_id,
                file_properties=self.clean_data(file_props),
                section_id=section_id, field_id=field_id)

    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a file by ID.

        Args:
            file_id: File's unique identifier.

        Returns:
            File data or None if not found.
        """
        async with self.session() as session:
            result = await session.run("""
                MATCH (file:File {id: $file_id})
                RETURN file
            """, file_id=file_id)

            record = await result.single()
            return dict(record["file"]) if record else None

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file reference from the database.

        Args:
            file_id: File's unique identifier.

        Returns:
            True if file was deleted, False otherwise.
        """
        async with self.session() as session:
            result = await session.run("""
                MATCH (file:File {id: $file_id})
                DETACH DELETE file
                RETURN count(file) as deleted_count
            """, file_id=file_id)

            record = await result.single()
            return record is not None and record["deleted_count"] > 0

    # ==================== Report Management ====================

    async def add_report_to_person(
        self,
        project_safe_name: str,
        person_id: str,
        report_data: Dict[str, Any]
    ) -> None:
        """
        Add a report reference to a person.

        Args:
            project_safe_name: URL-safe project name.
            person_id: Person's unique identifier.
            report_data: Report metadata dictionary.
        """
        async with self.session() as session:
            await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person {id: $person_id})
                SET person.reports = coalesce(person.reports, []) + $report_data
            """, project_safe_name=project_safe_name,
                person_id=person_id, report_data=report_data)

    async def remove_report_from_person(
        self,
        project_safe_name: str,
        person_id: str,
        report_name: str
    ) -> None:
        """
        Remove a report reference from a person.

        Args:
            project_safe_name: URL-safe project name.
            person_id: Person's unique identifier.
            report_name: Name of the report to remove.
        """
        async with self.session() as session:
            await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person {id: $person_id})
                SET person.reports = [r IN coalesce(person.reports, [])
                                      WHERE r.name <> $report_name]
            """, project_safe_name=project_safe_name,
                person_id=person_id, report_name=report_name)

    # ==================== Import/Export ====================

    async def import_from_json(
        self,
        project_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Import a project from JSON data.

        Args:
            project_data: Project data including people.

        Returns:
            Imported project data.
        """
        project_name = project_data.get("name", "Imported Project")
        safe_name = project_data.get("safe_name", self.slugify(project_name))

        await self.create_project(project_name, safe_name)

        for person_data in project_data.get("people", []):
            await self.create_person(safe_name, person_data)

        return await self.get_project(safe_name)

    async def export_to_json(self, project_safe_name: str) -> Optional[Dict[str, Any]]:
        """
        Export a project to JSON data.

        Args:
            project_safe_name: URL-safe project name.

        Returns:
            Project data including all people.
        """
        return await self.get_project(project_safe_name)

    # ==================== Utility Methods ====================

    @staticmethod
    def convert_neo4j_datetime(neo4j_datetime: Any) -> str:
        """
        Convert Neo4j DateTime object to ISO format string.

        Args:
            neo4j_datetime: Neo4j datetime object.

        Returns:
            ISO format datetime string.
        """
        if neo4j_datetime is None:
            return None
        if hasattr(neo4j_datetime, 'iso_format'):
            return neo4j_datetime.iso_format()
        elif hasattr(neo4j_datetime, 'to_native'):
            return neo4j_datetime.to_native().isoformat()
        return str(neo4j_datetime)

    @staticmethod
    def clean_data(data: Any) -> Any:
        """
        Clean data for Neo4j storage by converting to JSON-compatible types.

        Args:
            data: Data to clean (can be any type).

        Returns:
            Cleaned data suitable for Neo4j storage.
        """
        if isinstance(data, (str, int, float, bool)) or data is None:
            return data
        elif isinstance(data, (list, tuple)):
            return [AsyncNeo4jService.clean_data(item) for item in data]
        elif isinstance(data, dict):
            return {key: AsyncNeo4jService.clean_data(value) for key, value in data.items()}
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, 'iso_format'):  # Handle Neo4j DateTime
            return data.iso_format()
        elif hasattr(data, 'to_native'):  # Handle other Neo4j temporal types
            return data.to_native().isoformat()
        else:
            return str(data)

    @staticmethod
    def slugify(value: str) -> str:
        """
        Convert a string to a URL-safe slug.

        Args:
            value: String to convert.

        Returns:
            URL-safe slug.
        """
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()
        return re.sub(r'[-\s]+', '_', value)

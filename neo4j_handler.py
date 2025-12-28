from neo4j import GraphDatabase
import os
from datetime import datetime
from dotenv import load_dotenv
import json
from uuid import uuid4
import re
import time

# Load environment variables from .env
load_dotenv()

class Neo4jHandler:
    def __init__(self):
        """Initialize Neo4j connection using environment variables."""
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "neo4jbasset")
        self.driver = None

        # Wait for Neo4j to be available
        wait_start = time.time()
        while True:
            try:
                self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                # Try a simple query to test connection
                with self.driver.session() as session:
                    session.run("RETURN 1")
                break  # Success!
            except Exception as e:
                elapsed = int(time.time() - wait_start)
                print(f"\rWaiting to connect to Neo4j ({self.uri})... {elapsed}s", end='', flush=True)
                time.sleep(2)
        print(f"\rConnected to Neo4j at {self.uri} after {int(time.time() - wait_start)}s.{' ' * 20}")

        self.ensure_constraints()
    
    def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            self.driver.close()
    
    def ensure_constraints(self):
        """Set up constraints to ensure uniqueness and indexing."""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Project) REQUIRE p.safe_name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE",
                "CREATE INDEX IF NOT EXISTS FOR (p:Project) ON (p.name)",
                "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.created_at)",
                "CREATE INDEX IF NOT EXISTS FOR (s:Section) ON (s.id)",
                "CREATE INDEX IF NOT EXISTS FOR (f:Field) ON (f.id)",
                # Add relationship type existence check
                "CREATE INDEX IF NOT EXISTS FOR ()-[r:HAS_FILE]-() ON (r.section_id, r.field_id)"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Error creating constraint {constraint}: {e}")
    
    def setup_schema_from_config(self, config):
        """
        Create relationship types and properties based on the configuration.

        This method uses UNWIND for batch operations to avoid N+1 query patterns.
        """
        # Prepare batch data
        sections_data = []
        fields_data = []
        components_data = []

        for section in config.get("sections", []):
            section_id = section.get("id")
            section_label = section.get("label", section_id)
            sections_data.append({
                "id": section_id,
                "label": section_label
            })

            for field in section.get("fields", []):
                field_id = field.get("id")
                fields_data.append({
                    "id": field_id,
                    "section_id": section_id,
                    "label": field.get("label", field_id),
                    "type": field.get("type", "string"),
                    "multiple": field.get("multiple", False)
                })

                # Handle field components
                for component in field.get("components", []):
                    components_data.append({
                        "id": component.get("id"),
                        "field_id": field_id,
                        "section_id": section_id,
                        "label": component.get("label", component.get("id")),
                        "type": component.get("type", "string")
                    })

        with self.driver.session() as session:
            # Clear existing schema if needed
            session.run("""
                MATCH (c:Configuration {id: 'main'})
                DETACH DELETE c
            """)

            # Create new configuration and batch create all sections
            if sections_data:
                session.run("""
                    MERGE (config:Configuration {id: 'main'})
                    SET config.updated_at = $timestamp
                    WITH config
                    UNWIND $sections AS s
                    MERGE (section:Section {id: s.id})
                    SET section.label = s.label
                    MERGE (config)-[:HAS_SECTION]->(section)
                """, timestamp=datetime.now().isoformat(), sections=sections_data)

            # Batch create all fields
            if fields_data:
                session.run("""
                    UNWIND $fields AS f
                    MATCH (section:Section {id: f.section_id})
                    MERGE (field:Field {id: f.id})
                    SET field.section_id = f.section_id,
                        field.label = f.label,
                        field.type = f.type,
                        field.multiple = f.multiple
                    MERGE (section)-[:HAS_FIELD]->(field)
                """, fields=fields_data)

            # Batch create all components
            if components_data:
                session.run("""
                    UNWIND $components AS c
                    MATCH (field:Field {id: c.field_id})
                    MERGE (component:Component {id: c.id})
                    SET component.field_id = c.field_id,
                        component.section_id = c.section_id,
                        component.label = c.label,
                        component.type = c.type
                    MERGE (field)-[:HAS_COMPONENT]->(component)
                """, components=components_data)

    # In neo4j_handler.py, update create_project:
    def create_project(self, project_name, safe_name=None):
        """Create a new project in Neo4j."""
        if not safe_name:
            safe_name = self.slugify(project_name)
            
        with self.driver.session() as session:
            project_id = str(uuid4())  # Generate a UUID for the project
            result = session.run("""
                CREATE (p:Project {
                    id: $id,
                    name: $name,
                    safe_name: $safe_name,
                    start_date: datetime(),
                    created_at: datetime()
                })
                RETURN p
            """, id=project_id, name=project_name, safe_name=safe_name)
            
            record = result.single()
            if record:
                project_data = dict(record["p"])
                project_data["id"] = project_id  # Ensure ID is included
                return project_data
            return None

    def get_project(self, safe_name):
        """Retrieve a project by its safe name with all related data."""
        with self.driver.session() as session:
            # Get project basic info
            result = session.run("""
                MATCH (p:Project {safe_name: $safe_name})
                RETURN p
            """, safe_name=safe_name)
            
            project_record = result.single()
            if not project_record:
                return None
                
            project_data = dict(project_record["p"])
            project_data["people"] = self.get_all_people(safe_name)
            return project_data

    def get_all_projects(self):
        """Retrieve all projects with basic info."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Project)
                RETURN p.id as id, p.name as name, p.safe_name as safe_name, p.created_at as created_at
                ORDER BY p.created_at DESC
            """)
            
            projects = []
            for record in result:
                project = {
                    "id": record["id"],
                    "name": record["name"],
                    "safe_name": record["safe_name"],
                    "created_at": self.convert_neo4j_datetime(record["created_at"])
                }
                projects.append(project)
            return projects

    def convert_neo4j_datetime(self, neo4j_datetime):
        """Convert Neo4j DateTime object to ISO format string."""
        if hasattr(neo4j_datetime, 'iso_format'):
            return neo4j_datetime.iso_format()
        elif hasattr(neo4j_datetime, 'to_native'):
            return neo4j_datetime.to_native().isoformat()
        return str(neo4j_datetime)
    
    def update_project(self, safe_name, project_data):
        """Update project properties."""
        if "people" in project_data:
            del project_data["people"]
            
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Project {safe_name: $safe_name})
                SET p += $properties
                RETURN p
            """, safe_name=safe_name, properties=self.clean_data(project_data))
            
            record = result.single()
            return dict(record["p"]) if record else None
    
    def delete_project(self, safe_name):
        """Delete a project and all its associated data."""
        with self.driver.session() as session:
            # Delete all related data first
            session.run("""
                MATCH (project:Project {safe_name: $safe_name})-[:HAS_PERSON]->(person:Person)
                OPTIONAL MATCH (person)-[:HAS_FILE]->(file:File)
                DETACH DELETE person, file
            """, safe_name=safe_name)
            
            # Then delete the project
            result = session.run("""
                MATCH (p:Project {safe_name: $safe_name})
                DETACH DELETE p
                RETURN count(p) as deleted_count
            """, safe_name=safe_name)
            
            record = result.single()
            return record and record["deleted_count"] > 0
    
    def create_person(self, project_safe_name, person_data=None):
        """Create a new person in a project."""
        # Use the provided ID if present, otherwise generate one
        if person_data and "id" in person_data:
            person_id = person_data["id"]
        else:
            person_id = str(uuid4())
            if person_data is not None:
                person_data["id"] = person_id

        # Use the provided created_at if present, otherwise set now
        now = person_data.get("created_at") if person_data and "created_at" in person_data else datetime.now().isoformat()
        if person_data is not None:
            person_data["created_at"] = now

        if not person_data:
            person_data = {"profile": {}}

        with self.driver.session() as session:
            # First verify project exists
            project = session.run("""
                MATCH (p:Project {safe_name: $project_safe_name})
                RETURN p
            """, project_safe_name=project_safe_name).single()
            
            if not project:
                return None
            
            # Create person node and link to project
            result = session.run("""
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
            
            if not result.single():
                return None
            
            # Process profile data
            if "profile" in person_data:
                for section_id, fields in person_data["profile"].items():
                    for field_id, value in fields.items():
                        if isinstance(value, (dict, list)):
                            # Convert complex objects to JSON strings
                            value = json.dumps(value)
                        self.set_person_field(person_id, section_id, field_id, value)
            
            return self.get_person(project_safe_name, person_id)
    
    def get_person(self, project_safe_name, person_id):
        """Retrieve a person by ID within a project."""
        with self.driver.session() as session:
            # Get basic person info
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(person:Person {id: $person_id})
                RETURN person
            """, project_safe_name=project_safe_name, person_id=person_id)
            
            record = result.single()
            if not record:
                return None
                
            person_data = dict(record["person"])
            person_data["profile"] = {}
            
            # Get all profile data
            profile_result = session.run("""
                MATCH (person:Person {id: $person_id})-[:HAS_FIELD_VALUE]->(fv:FieldValue)
                RETURN fv.section_id as section_id, fv.field_id as field_id, fv.value as value
            """, person_id=person_id)
            
            for field_record in profile_result:
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
            files_result = session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FILE]->(file:File)
                RETURN file, r.section_id as section_id, r.field_id as field_id
            """, person_id=person_id)
            
            for file_record in files_result:
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

    def get_all_people(self, project_safe_name):
        """
        Retrieve all people in a project with all their data in a single query.

        This method uses COLLECT to aggregate all related data (field values and files)
        in a single query, avoiding N+1 query patterns.
        """
        with self.driver.session() as session:
            # Single optimized query that fetches all people with their field values and files
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person)
                OPTIONAL MATCH (person)-[:HAS_FIELD_VALUE]->(fv:FieldValue)
                OPTIONAL MATCH (person)-[file_rel:HAS_FILE]->(file:File)
                WITH person,
                     COLLECT(DISTINCT {
                         section_id: fv.section_id,
                         field_id: fv.field_id,
                         value: fv.value
                     }) AS field_values,
                     COLLECT(DISTINCT {
                         file: file,
                         section_id: file_rel.section_id,
                         field_id: file_rel.field_id
                     }) AS files
                RETURN person, field_values, files
                ORDER BY person.created_at DESC
            """, project_safe_name=project_safe_name)

            people = []
            for record in result:
                person_data = dict(record["person"])
                person_data["profile"] = {}

                # Process field values
                for fv in record["field_values"]:
                    # Skip empty field values (from OPTIONAL MATCH with no results)
                    if fv["section_id"] is None:
                        continue

                    section_id = fv["section_id"]
                    field_id = fv["field_id"]
                    value = fv["value"]

                    if section_id not in person_data["profile"]:
                        person_data["profile"][section_id] = {}

                    # Try to parse JSON strings
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass

                    person_data["profile"][section_id][field_id] = value

                # Process files
                for file_data in record["files"]:
                    # Skip empty file entries (from OPTIONAL MATCH with no results)
                    if file_data["file"] is None:
                        continue

                    file_info = dict(file_data["file"])
                    section_id = file_data["section_id"]
                    field_id = file_data["field_id"]

                    if section_id not in person_data["profile"]:
                        person_data["profile"][section_id] = {}

                    if field_id not in person_data["profile"][section_id]:
                        person_data["profile"][section_id][field_id] = []

                    if isinstance(person_data["profile"][section_id][field_id], list):
                        person_data["profile"][section_id][field_id].append(file_info)
                    else:
                        person_data["profile"][section_id][field_id] = file_info

                people.append(person_data)

            return people

    def get_people_batch(self, project_safe_name, entity_ids):
        """
        Retrieve multiple people by their IDs in a single query.

        This method uses UNWIND to fetch multiple entities efficiently,
        avoiding N+1 query patterns when retrieving multiple people.

        Args:
            project_safe_name: The project's safe name
            entity_ids: List of entity IDs to retrieve

        Returns:
            Dict mapping entity_id to person data
        """
        if not entity_ids:
            return {}

        with self.driver.session() as session:
            # Single optimized query that fetches all requested people with their data
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                UNWIND $entity_ids AS eid
                MATCH (project)-[:HAS_PERSON]->(person:Person {id: eid})
                OPTIONAL MATCH (person)-[:HAS_FIELD_VALUE]->(fv:FieldValue)
                OPTIONAL MATCH (person)-[file_rel:HAS_FILE]->(file:File)
                WITH person,
                     COLLECT(DISTINCT {
                         section_id: fv.section_id,
                         field_id: fv.field_id,
                         value: fv.value
                     }) AS field_values,
                     COLLECT(DISTINCT {
                         file: file,
                         section_id: file_rel.section_id,
                         field_id: file_rel.field_id
                     }) AS files
                RETURN person, field_values, files
            """, project_safe_name=project_safe_name, entity_ids=list(entity_ids))

            people_map = {}
            for record in result:
                person_data = dict(record["person"])
                person_data["profile"] = {}

                # Process field values
                for fv in record["field_values"]:
                    if fv["section_id"] is None:
                        continue

                    section_id = fv["section_id"]
                    field_id = fv["field_id"]
                    value = fv["value"]

                    if section_id not in person_data["profile"]:
                        person_data["profile"][section_id] = {}

                    # Try to parse JSON strings
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass

                    person_data["profile"][section_id][field_id] = value

                # Process files
                for file_data in record["files"]:
                    if file_data["file"] is None:
                        continue

                    file_info = dict(file_data["file"])
                    section_id = file_data["section_id"]
                    field_id = file_data["field_id"]

                    if section_id not in person_data["profile"]:
                        person_data["profile"][section_id] = {}

                    if field_id not in person_data["profile"][section_id]:
                        person_data["profile"][section_id][field_id] = []

                    if isinstance(person_data["profile"][section_id][field_id], list):
                        person_data["profile"][section_id][field_id].append(file_info)
                    else:
                        person_data["profile"][section_id][field_id] = file_info

                people_map[person_data["id"]] = person_data

            return people_map

    def get_all_people_paginated(self, project_safe_name, offset=0, limit=100):
        """
        Retrieve people in a project with database-level pagination.

        This method uses SKIP and LIMIT in the Cypher query for efficient
        pagination without loading all data into memory.

        Args:
            project_safe_name: The project's safe name
            offset: Number of records to skip (default 0)
            limit: Maximum number of records to return (default 100)

        Returns:
            List of person data dictionaries
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person)
                WITH person
                ORDER BY person.created_at DESC
                SKIP $offset
                LIMIT $limit
                OPTIONAL MATCH (person)-[:HAS_FIELD_VALUE]->(fv:FieldValue)
                OPTIONAL MATCH (person)-[file_rel:HAS_FILE]->(file:File)
                WITH person,
                     COLLECT(DISTINCT {
                         section_id: fv.section_id,
                         field_id: fv.field_id,
                         value: fv.value
                     }) AS field_values,
                     COLLECT(DISTINCT {
                         file: file,
                         section_id: file_rel.section_id,
                         field_id: file_rel.field_id
                     }) AS files
                RETURN person, field_values, files
            """, project_safe_name=project_safe_name, offset=offset, limit=limit)

            people = []
            for record in result:
                person_data = dict(record["person"])
                person_data["profile"] = {}

                # Process field values
                for fv in record["field_values"]:
                    if fv["section_id"] is None:
                        continue

                    section_id = fv["section_id"]
                    field_id = fv["field_id"]
                    value = fv["value"]

                    if section_id not in person_data["profile"]:
                        person_data["profile"][section_id] = {}

                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass

                    person_data["profile"][section_id][field_id] = value

                # Process files
                for file_data in record["files"]:
                    if file_data["file"] is None:
                        continue

                    file_info = dict(file_data["file"])
                    section_id = file_data["section_id"]
                    field_id = file_data["field_id"]

                    if section_id not in person_data["profile"]:
                        person_data["profile"][section_id] = {}

                    if field_id not in person_data["profile"][section_id]:
                        person_data["profile"][section_id][field_id] = []

                    if isinstance(person_data["profile"][section_id][field_id], list):
                        person_data["profile"][section_id][field_id].append(file_info)
                    else:
                        person_data["profile"][section_id][field_id] = file_info

                people.append(person_data)

            return people

    def get_people_count(self, project_safe_name):
        """
        Get the total count of people in a project.

        This is useful for pagination calculations without loading all data.

        Args:
            project_safe_name: The project's safe name

        Returns:
            Integer count of people in the project
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person)
                RETURN count(person) AS count
            """, project_safe_name=project_safe_name)

            record = result.single()
            return record["count"] if record else 0

    def update_person(self, project_safe_name, person_id, updated_data):
        """Update a person's data."""
        profile_data = updated_data.pop("profile", {}) if "profile" in updated_data else {}
        
        with self.driver.session() as session:
            # Update basic person info
            if updated_data:
                result = session.run("""
                    MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(person:Person {id: $person_id})
                    SET person += $properties
                    RETURN person
                """, project_safe_name=project_safe_name, 
                    person_id=person_id, properties=self.clean_data(updated_data))
                
                if not result.single():
                    return None
            
            # Update profile data
            for section_id, fields in profile_data.items():
                for field_id, value in fields.items():
                    self.set_person_field(person_id, section_id, field_id, value)
            
            return self.get_person(project_safe_name, person_id)
    
    def set_person_field(self, person_id, section_id, field_id, value):
        """Set a specific field value for a person."""
        with self.driver.session() as session:
            # First delete any existing value for this field
            session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FIELD_VALUE]->(fv:FieldValue)
                WHERE fv.section_id = $section_id AND fv.field_id = $field_id
                DELETE r, fv
            """, person_id=person_id, section_id=section_id, field_id=field_id)
            
            # Handle file fields differently
            if isinstance(value, dict) and "path" in value:
                return self.handle_file_upload(
                    person_id=person_id,
                    section_id=section_id,
                    field_id=field_id,
                    file_id=value.get("id", str(uuid4())),
                    filename=value.get("name", ""),
                    file_path=value.get("path", ""),
                    metadata=value
                )
            elif isinstance(value, list) and value and isinstance(value[0], dict) and "path" in value[0]:
                for file_data in value:
                    self.handle_file_upload(
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
            session.run("""
                MATCH (person:Person {id: $person_id})
                CREATE (fv:FieldValue {
                    section_id: $section_id,
                    field_id: $field_id,
                    value: $value
                })
                CREATE (person)-[:HAS_FIELD_VALUE]->(fv)
            """, person_id=person_id, section_id=section_id,
                field_id=field_id, value=value)

    def set_person_fields_batch(self, person_id, profile_data):
        """
        Set multiple field values for a person in a batch operation.

        This method uses UNWIND to create multiple field values in a single query,
        avoiding N+1 query patterns when setting multiple fields.

        Args:
            person_id: Person's unique identifier.
            profile_data: Dictionary of section_id -> {field_id -> value} mappings.
        """
        if not profile_data:
            return

        # Separate regular field values from file uploads
        field_values = []
        file_uploads = []

        for section_id, fields in profile_data.items():
            for field_id, value in fields.items():
                # Check if this is a file field
                if isinstance(value, dict) and "path" in value:
                    file_uploads.append({
                        "section_id": section_id,
                        "field_id": field_id,
                        "file_id": value.get("id", str(uuid4())),
                        "filename": value.get("name", ""),
                        "file_path": value.get("path", ""),
                        "metadata": value
                    })
                elif isinstance(value, list) and value and isinstance(value[0], dict) and "path" in value[0]:
                    for file_data in value:
                        file_uploads.append({
                            "section_id": section_id,
                            "field_id": field_id,
                            "file_id": file_data.get("id", str(uuid4())),
                            "filename": file_data.get("name", ""),
                            "file_path": file_data.get("path", ""),
                            "metadata": file_data
                        })
                else:
                    # Convert complex objects to JSON strings
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    field_values.append({
                        "section_id": section_id,
                        "field_id": field_id,
                        "value": value
                    })

        with self.driver.session() as session:
            # First, batch delete existing field values for all fields we're updating
            if field_values:
                field_keys = [{"section_id": fv["section_id"], "field_id": fv["field_id"]} for fv in field_values]
                session.run("""
                    UNWIND $field_keys AS fk
                    MATCH (person:Person {id: $person_id})-[r:HAS_FIELD_VALUE]->(fv:FieldValue)
                    WHERE fv.section_id = fk.section_id AND fv.field_id = fk.field_id
                    DELETE r, fv
                """, person_id=person_id, field_keys=field_keys)

                # Batch create new field values
                session.run("""
                    MATCH (person:Person {id: $person_id})
                    UNWIND $field_values AS fv
                    CREATE (field_value:FieldValue {
                        section_id: fv.section_id,
                        field_id: fv.field_id,
                        value: fv.value
                    })
                    CREATE (person)-[:HAS_FIELD_VALUE]->(field_value)
                """, person_id=person_id, field_values=field_values)

        # Handle file uploads using batch method
        if file_uploads:
            self.handle_file_uploads_batch(person_id, file_uploads)

    def handle_file_uploads_batch(self, person_id, file_uploads):
        """
        Handle multiple file uploads in a batch operation.

        This method uses UNWIND to create multiple file nodes and relationships
        in a single query, avoiding N+1 query patterns.

        Args:
            person_id: Person's unique identifier.
            file_uploads: List of file upload dictionaries.
        """
        if not file_uploads:
            return

        # Prepare file properties for batch operation
        now = datetime.now().isoformat()
        file_data_list = []

        for upload in file_uploads:
            file_props = {
                "id": upload["file_id"],
                "name": upload["filename"],
                "path": upload["file_path"],
                "section_id": upload["section_id"],
                "field_id": upload["field_id"],
                "person_id": person_id,
                "uploaded_at": now
            }
            if upload.get("metadata"):
                file_props.update(upload["metadata"])

            file_data_list.append({
                "file_props": self.clean_data(file_props),
                "section_id": upload["section_id"],
                "field_id": upload["field_id"]
            })

        with self.driver.session() as session:
            # First, batch delete existing files for the fields we're updating
            field_keys = [{"section_id": fd["section_id"], "field_id": fd["field_id"]} for fd in file_data_list]
            session.run("""
                UNWIND $field_keys AS fk
                MATCH (person:Person {id: $person_id})-[r:HAS_FILE]->(file:File)
                WHERE file.section_id = fk.section_id AND file.field_id = fk.field_id
                DELETE r, file
            """, person_id=person_id, field_keys=field_keys)

            # Batch create new file nodes and relationships
            session.run("""
                MATCH (person:Person {id: $person_id})
                UNWIND $file_data_list AS fd
                CREATE (file:File)
                SET file = fd.file_props
                CREATE (person)-[r:HAS_FILE]->(file)
                SET r.section_id = fd.section_id,
                    r.field_id = fd.field_id
            """, person_id=person_id, file_data_list=file_data_list)

    def delete_person(self, project_safe_name, person_id):
        """
        Delete a person and all their associated data in a single query.

        This method uses a single optimized query to delete the person and all
        related data, avoiding multiple round trips to the database.
        """
        with self.driver.session() as session:
            # Single query to verify, delete related data, and delete person
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person {id: $person_id})
                OPTIONAL MATCH (person)-[fv_rel:HAS_FIELD_VALUE]->(fv:FieldValue)
                OPTIONAL MATCH (person)-[file_rel:HAS_FILE]->(file:File)
                WITH person, COLLECT(DISTINCT fv) AS field_values,
                     COLLECT(DISTINCT file) AS files,
                     COLLECT(DISTINCT fv_rel) AS fv_rels,
                     COLLECT(DISTINCT file_rel) AS file_rels
                FOREACH (r IN fv_rels | DELETE r)
                FOREACH (f IN field_values | DELETE f)
                FOREACH (r IN file_rels | DELETE r)
                FOREACH (f IN files | DELETE f)
                DETACH DELETE person
                RETURN count(person) as deleted_count
            """, project_safe_name=project_safe_name, person_id=person_id)

            record = result.single()
            return record is not None and record["deleted_count"] > 0
    
    def handle_file_upload(self, person_id, section_id, field_id, file_id, filename, file_path, metadata=None):
        """Handle file upload and create appropriate relationships."""
        file_props = {
            "id": file_id,
            "name": filename,
            "path": file_path,
            "section_id": section_id,
            "field_id": field_id,
            "person_id": person_id,  # Ensure person_id is stored
            "uploaded_at": datetime.now().isoformat()
        }
        
        if metadata:
            file_props.update(metadata)
        
        with self.driver.session() as session:
            # First delete any existing file with this field reference
            session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FILE]->(file:File)
                WHERE file.section_id = $section_id AND file.field_id = $field_id
                DELETE r, file
            """, person_id=person_id, section_id=section_id, field_id=field_id)
            
            # Create new file node and relationship with properties
            session.run("""
                MATCH (person:Person {id: $person_id})
                MERGE (file:File {id: $file_id})
                SET file = $file_properties
                MERGE (person)-[r:HAS_FILE]->(file)
                SET r.section_id = $section_id,
                    r.field_id = $field_id
            """, person_id=person_id, file_id=file_id, 
                file_properties=self.clean_data(file_props),
                section_id=section_id, field_id=field_id)

    def get_file(self, file_id):
        """Retrieve a file by ID."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (file:File {id: $file_id})
                RETURN file
            """, file_id=file_id)
            
            record = result.single()
            return dict(record["file"]) if record else None
    
    def delete_file(self, file_id):
        """Delete a file reference from the database."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (file:File {id: $file_id})
                DETACH DELETE file
                RETURN count(file) as deleted_count
            """, file_id=file_id)
            
            record = result.single()
            return record and record["deleted_count"] > 0
    
    def import_from_json(self, project_data):
        """Import a project from JSON data."""
        project_name = project_data.get("name", "Imported Project")
        safe_name = project_data.get("safe_name", self.slugify(project_name))
        
        self.create_project(project_name, safe_name)
        
        for person_data in project_data.get("people", []):
            self.create_person(safe_name, person_data)
        
        return self.get_project(safe_name)
    
    def export_to_json(self, project_safe_name):
        """Export a project to JSON data."""
        return self.get_project(project_safe_name)
    
    # In neo4j_handler.py, update the clean_data method:
    def clean_data(self, data):
        """Clean data for Neo4j storage by converting to JSON-compatible types."""
        if isinstance(data, (str, int, float, bool)) or data is None:
            return data
        elif isinstance(data, (list, tuple)):
            return [self.clean_data(item) for item in data]
        elif isinstance(data, dict):
            return {key: self.clean_data(value) for key, value in data.items()}
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, 'iso_format'):  # Handle Neo4j DateTime
            return data.iso_format()
        elif hasattr(data, 'to_native'):  # Handle other Neo4j temporal types
            return data.to_native().isoformat()
        else:
            return str(data)
    
    def add_report_to_person(self, project_safe_name, person_id, report_data):
        """Add a report reference to a person in Neo4j."""
        with self.driver.session() as session:
            # Store reports as a list in the profile under 'reports'
            session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(person:Person {id: $person_id})
                SET person.reports = coalesce(person.reports, []) + $report_data
            """, project_safe_name=project_safe_name, person_id=person_id, report_data=report_data)

    def remove_report_from_person(self, project_safe_name, person_id, report_name):
        """Remove a report reference from a person in Neo4j."""
        with self.driver.session() as session:
            # Remove the report with the given name from the reports list
            session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(person:Person {id: $person_id})
                SET person.reports = [r IN coalesce(person.reports, []) WHERE r.name <> $report_name]
            """, project_safe_name=project_safe_name, person_id=person_id, report_name=report_name)

    @staticmethod
    def slugify(value):
        """Convert a string to a slug."""
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()
        return re.sub(r'[-\s]+', '_', value)

    # =============================================================================
    # Graph Analysis Methods
    # =============================================================================

    def find_shortest_path(self, project_safe_name, entity_id_1, entity_id_2):
        """
        Find the shortest path between two entities in a project.

        Uses Neo4j's shortestPath algorithm to find the most direct connection
        between two entities through their relationships (tagged people).

        Args:
            project_safe_name: The project's safe name
            entity_id_1: The starting entity ID
            entity_id_2: The target entity ID

        Returns:
            dict with path information including nodes and relationships, or None if no path exists
        """
        with self.driver.session() as session:
            # First verify both entities exist in the project
            verify = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(p1:Person {id: $id1})
                MATCH (project)-[:HAS_PERSON]->(p2:Person {id: $id2})
                RETURN p1, p2
            """, project_safe_name=project_safe_name, id1=entity_id_1, id2=entity_id_2)

            if not verify.single():
                return None

            # Find shortest path using tagged_people relationships stored in FieldValue nodes
            # We need to traverse: Person -> FieldValue (tagged_people) -> Person
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(start:Person {id: $id1})
                MATCH (project)-[:HAS_PERSON]->(end:Person {id: $id2})
                MATCH path = shortestPath((start)-[*..15]-(end))
                RETURN path,
                       [node IN nodes(path) WHERE node:Person | node.id] AS entity_ids,
                       length(path) AS path_length
                LIMIT 1
            """, project_safe_name=project_safe_name, id1=entity_id_1, id2=entity_id_2)

            record = result.single()
            if not record:
                return {"found": False, "message": "No path found between entities"}

            entity_ids = record["entity_ids"]
            path_length = record["path_length"]

            # Get full entity data for each node in path using batch query
            entities_map = self.get_people_batch(project_safe_name, entity_ids)
            entities = [entities_map[eid] for eid in entity_ids if eid in entities_map]

            return {
                "found": True,
                "path_length": path_length,
                "entity_count": len(entities),
                "entity_ids": entity_ids,
                "entities": entities
            }

    def find_all_paths(self, project_safe_name, entity_id_1, entity_id_2, max_depth=5):
        """
        Find all paths between two entities up to a maximum depth.

        Args:
            project_safe_name: The project's safe name
            entity_id_1: The starting entity ID
            entity_id_2: The target entity ID
            max_depth: Maximum path length to search (default 5)

        Returns:
            list of path dictionaries, each containing nodes and length
        """
        with self.driver.session() as session:
            # Find all paths up to max_depth
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(start:Person {id: $id1})
                MATCH (project)-[:HAS_PERSON]->(end:Person {id: $id2})
                MATCH path = (start)-[*1..$max_depth]-(end)
                WITH path, [node IN nodes(path) WHERE node:Person | node.id] AS entity_ids
                WHERE size(entity_ids) >= 2
                RETURN DISTINCT entity_ids, length(path) AS path_length
                ORDER BY path_length
                LIMIT 50
            """, project_safe_name=project_safe_name, id1=entity_id_1, id2=entity_id_2, max_depth=max_depth)

            paths = []
            seen_paths = set()

            for record in result:
                entity_ids = record["entity_ids"]
                path_key = tuple(entity_ids)

                if path_key not in seen_paths:
                    seen_paths.add(path_key)
                    paths.append({
                        "entity_ids": entity_ids,
                        "path_length": record["path_length"],
                        "entity_count": len(entity_ids)
                    })

            return {
                "found": len(paths) > 0,
                "path_count": len(paths),
                "max_depth_searched": max_depth,
                "paths": paths
            }

    def get_entity_centrality(self, project_safe_name, entity_id):
        """
        Calculate degree centrality for an entity (number of direct connections).

        Degree centrality measures how connected an entity is by counting
        both incoming and outgoing relationships.

        Args:
            project_safe_name: The project's safe name
            entity_id: The entity ID to analyze

        Returns:
            dict with centrality metrics
        """
        with self.driver.session() as session:
            # Get the entity and count its connections
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(person:Person {id: $entity_id})

                // Count outgoing connections (entities this person tagged)
                OPTIONAL MATCH (person)-[:HAS_FIELD_VALUE]->(fv:FieldValue)
                WHERE fv.field_id = 'tagged_people'

                // Count incoming connections (entities that tagged this person)
                OPTIONAL MATCH (other:Person)-[:HAS_FIELD_VALUE]->(ofv:FieldValue)
                WHERE ofv.field_id = 'tagged_people' AND other.id <> $entity_id

                RETURN person.id AS entity_id,
                       person.created_at AS created_at
            """, project_safe_name=project_safe_name, entity_id=entity_id)

            record = result.single()
            if not record:
                return None

            # Get the actual connections by checking the profile data
            entity = self.get_person(project_safe_name, entity_id)
            if not entity:
                return None

            # Outgoing: entities this person tagged
            profile = entity.get("profile", {})
            tagged_section = profile.get("Tagged People", {})
            tagged_people = tagged_section.get("tagged_people", [])
            if not isinstance(tagged_people, list):
                tagged_people = [tagged_people] if tagged_people else []
            outgoing_count = len(tagged_people)

            # Incoming: entities that tagged this person
            all_people = self.get_all_people(project_safe_name)
            incoming_count = 0
            incoming_from = []

            for person in all_people:
                if person.get("id") == entity_id:
                    continue
                person_tagged = person.get("profile", {}).get("Tagged People", {}).get("tagged_people", [])
                if not isinstance(person_tagged, list):
                    person_tagged = [person_tagged] if person_tagged else []
                if entity_id in person_tagged:
                    incoming_count += 1
                    incoming_from.append(person.get("id"))

            total_connections = outgoing_count + incoming_count

            # Calculate normalized centrality (if there are other entities)
            total_entities = len(all_people)
            max_possible = (total_entities - 1) * 2 if total_entities > 1 else 1
            normalized_centrality = total_connections / max_possible if max_possible > 0 else 0

            return {
                "entity_id": entity_id,
                "degree_centrality": total_connections,
                "outgoing_connections": outgoing_count,
                "incoming_connections": incoming_count,
                "outgoing_to": tagged_people,
                "incoming_from": incoming_from,
                "normalized_centrality": round(normalized_centrality, 4),
                "total_entities_in_project": total_entities
            }

    def get_most_connected(self, project_safe_name, limit=10):
        """
        Find the most connected entities in a project.

        Returns entities ranked by their total degree centrality
        (sum of incoming and outgoing connections).

        Args:
            project_safe_name: The project's safe name
            limit: Maximum number of entities to return (default 10)

        Returns:
            list of entities with their connection counts, sorted by total connections
        """
        all_people = self.get_all_people(project_safe_name)

        if not all_people:
            return {"entities": [], "count": 0}

        # Build a map of who tagged whom
        tagged_by = {}  # entity_id -> list of entities that tagged them
        tags_to = {}    # entity_id -> list of entities they tagged

        for person in all_people:
            person_id = person.get("id")
            tagged_section = person.get("profile", {}).get("Tagged People", {})
            tagged_people = tagged_section.get("tagged_people", [])

            if not isinstance(tagged_people, list):
                tagged_people = [tagged_people] if tagged_people else []

            tags_to[person_id] = tagged_people

            for tagged_id in tagged_people:
                if tagged_id not in tagged_by:
                    tagged_by[tagged_id] = []
                tagged_by[tagged_id].append(person_id)

        # Calculate centrality for each entity
        entity_stats = []
        for person in all_people:
            person_id = person.get("id")
            outgoing = len(tags_to.get(person_id, []))
            incoming = len(tagged_by.get(person_id, []))
            total = outgoing + incoming

            entity_stats.append({
                "entity_id": person_id,
                "entity": person,
                "outgoing_connections": outgoing,
                "incoming_connections": incoming,
                "total_connections": total
            })

        # Sort by total connections (descending)
        entity_stats.sort(key=lambda x: x["total_connections"], reverse=True)

        # Return top N
        top_entities = entity_stats[:limit]

        return {
            "entities": top_entities,
            "count": len(top_entities),
            "total_entities_analyzed": len(all_people)
        }

    def get_entity_neighborhood(self, project_safe_name, entity_id, depth=2):
        """
        Get all entities within N hops of a given entity.

        This creates an ego network centered on the specified entity,
        including all entities reachable within the specified depth.

        Args:
            project_safe_name: The project's safe name
            entity_id: The center entity ID
            depth: Maximum number of hops (default 2)

        Returns:
            dict with neighborhood entities organized by distance
        """
        entity = self.get_person(project_safe_name, entity_id)
        if not entity:
            return None

        all_people = self.get_all_people(project_safe_name)

        # Build adjacency map (bidirectional)
        adjacency = {}
        for person in all_people:
            person_id = person.get("id")
            adjacency[person_id] = set()

            tagged_section = person.get("profile", {}).get("Tagged People", {})
            tagged_people = tagged_section.get("tagged_people", [])

            if not isinstance(tagged_people, list):
                tagged_people = [tagged_people] if tagged_people else []

            for tagged_id in tagged_people:
                adjacency[person_id].add(tagged_id)
                # Also add reverse connection for bidirectional traversal
                if tagged_id not in adjacency:
                    adjacency[tagged_id] = set()
                adjacency[tagged_id].add(person_id)

        # BFS to find all entities within depth
        visited = {entity_id: 0}
        queue = [(entity_id, 0)]
        levels = {0: [entity_id]}

        while queue:
            current_id, current_depth = queue.pop(0)

            if current_depth >= depth:
                continue

            neighbors = adjacency.get(current_id, set())
            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    new_depth = current_depth + 1
                    visited[neighbor_id] = new_depth
                    queue.append((neighbor_id, new_depth))

                    if new_depth not in levels:
                        levels[new_depth] = []
                    levels[new_depth].append(neighbor_id)

        # Build result with entity data using batch query
        all_neighborhood_ids = list(visited.keys())
        entities_map = self.get_people_batch(project_safe_name, all_neighborhood_ids)

        neighborhood = {}
        for level, entity_ids_at_level in levels.items():
            neighborhood[f"depth_{level}"] = []
            for eid in entity_ids_at_level:
                if eid in entities_map:
                    neighborhood[f"depth_{level}"].append(entities_map[eid])

        # Collect all edges within the neighborhood
        neighborhood_ids = set(visited.keys())
        edges = []
        for person in all_people:
            person_id = person.get("id")
            if person_id not in neighborhood_ids:
                continue

            tagged_section = person.get("profile", {}).get("Tagged People", {})
            tagged_people = tagged_section.get("tagged_people", [])

            if not isinstance(tagged_people, list):
                tagged_people = [tagged_people] if tagged_people else []

            for tagged_id in tagged_people:
                if tagged_id in neighborhood_ids:
                    edges.append({
                        "source": person_id,
                        "target": tagged_id
                    })

        return {
            "center_entity_id": entity_id,
            "max_depth": depth,
            "total_entities": len(visited),
            "neighborhood": neighborhood,
            "edges": edges
        }

    def find_clusters(self, project_safe_name):
        """
        Detect connected components/clusters in the project's entity graph.

        Uses union-find algorithm to identify groups of entities that are
        connected to each other but not to other groups.

        Args:
            project_safe_name: The project's safe name

        Returns:
            dict with cluster information including sizes and members
        """
        all_people = self.get_all_people(project_safe_name)

        if not all_people:
            return {"clusters": [], "cluster_count": 0, "isolated_count": 0}

        # Build adjacency map (bidirectional)
        entity_ids = [p.get("id") for p in all_people]
        adjacency = {eid: set() for eid in entity_ids}

        for person in all_people:
            person_id = person.get("id")
            tagged_section = person.get("profile", {}).get("Tagged People", {})
            tagged_people = tagged_section.get("tagged_people", [])

            if not isinstance(tagged_people, list):
                tagged_people = [tagged_people] if tagged_people else []

            for tagged_id in tagged_people:
                if tagged_id in adjacency:
                    adjacency[person_id].add(tagged_id)
                    adjacency[tagged_id].add(person_id)

        # Union-Find to detect connected components
        parent = {eid: eid for eid in entity_ids}

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Connect all adjacent entities
        for eid, neighbors in adjacency.items():
            for neighbor in neighbors:
                union(eid, neighbor)

        # Group entities by their root parent
        clusters_map = {}
        for eid in entity_ids:
            root = find(eid)
            if root not in clusters_map:
                clusters_map[root] = []
            clusters_map[root].append(eid)

        # Fetch all entities once using batch query
        all_entity_ids = list(entity_ids)
        entities_map = self.get_people_batch(project_safe_name, all_entity_ids)

        # Build cluster information
        clusters = []
        isolated_count = 0

        for root, members in clusters_map.items():
            if len(members) == 1:
                isolated_count += 1

            # Get entity data for cluster members from the batch-fetched map
            member_entities = [entities_map[eid] for eid in members if eid in entities_map]

            # Count internal edges
            internal_edges = 0
            for eid in members:
                for neighbor in adjacency.get(eid, set()):
                    if neighbor in members:
                        internal_edges += 1
            internal_edges //= 2  # Divide by 2 since we count each edge twice

            clusters.append({
                "cluster_id": root,
                "size": len(members),
                "entity_ids": members,
                "entities": member_entities,
                "internal_edges": internal_edges,
                "is_isolated": len(members) == 1
            })

        # Sort clusters by size (descending)
        clusters.sort(key=lambda x: x["size"], reverse=True)

        return {
            "cluster_count": len(clusters),
            "isolated_count": isolated_count,
            "connected_clusters": len([c for c in clusters if not c["is_isolated"]]),
            "total_entities": len(entity_ids),
            "clusters": clusters
        }

    # =============================================================================
    # Named Relationship Methods
    # =============================================================================

    def create_relationship(self, project_safe_name, source_id, target_id,
                           relationship_type="RELATED_TO", properties=None):
        """
        Create a named relationship between two persons.

        Args:
            project_safe_name: The project's safe name
            source_id: The source person's ID
            target_id: The target person's ID
            relationship_type: Type of relationship (e.g., WORKS_WITH, FRIEND)
            properties: Dict with additional properties (confidence, source, notes, etc.)

        Returns:
            Dict with relationship details or None if failed
        """
        if properties is None:
            properties = {}

        # Add timestamp if not provided
        if "timestamp" not in properties:
            properties["timestamp"] = datetime.now().isoformat()

        # Verify both persons exist
        source = self.get_person(project_safe_name, source_id)
        target = self.get_person(project_safe_name, target_id)

        if not source or not target:
            return None

        # Get existing tagged people data
        profile = source.get("profile", {})
        tagged_section = profile.get("Tagged People", {})
        tagged_ids = tagged_section.get("tagged_people", []) or []
        transitive = tagged_section.get("transitive_relationships", []) or []
        relationship_types = tagged_section.get("relationship_types", {}) or {}
        relationship_properties = tagged_section.get("relationship_properties", {}) or {}

        # Ensure lists and dicts
        if not isinstance(tagged_ids, list):
            tagged_ids = [tagged_ids] if tagged_ids else []
        if not isinstance(relationship_types, dict):
            relationship_types = {}
        if not isinstance(relationship_properties, dict):
            relationship_properties = {}

        # Add target to tagged list if not present
        if target_id not in tagged_ids:
            tagged_ids.append(target_id)

        # Set relationship type
        relationship_types[target_id] = relationship_type

        # Set relationship properties
        rel_props = {
            "relationship_type": relationship_type,
            "timestamp": properties.get("timestamp", datetime.now().isoformat()),
        }
        if "confidence" in properties:
            rel_props["confidence"] = properties["confidence"]
        if "source" in properties:
            rel_props["source"] = properties["source"]
        if "notes" in properties:
            rel_props["notes"] = properties["notes"]
        if "start_date" in properties:
            rel_props["start_date"] = properties["start_date"]
        if "end_date" in properties:
            rel_props["end_date"] = properties["end_date"]
        if "is_active" in properties:
            rel_props["is_active"] = properties["is_active"]
        if "verified_by" in properties:
            rel_props["verified_by"] = properties["verified_by"]
        if "verified_at" in properties:
            rel_props["verified_at"] = properties["verified_at"]

        relationship_properties[target_id] = rel_props

        # Update the person
        updated_data = {
            "profile": {
                "Tagged People": {
                    "tagged_people": tagged_ids,
                    "transitive_relationships": transitive,
                    "relationship_types": relationship_types,
                    "relationship_properties": relationship_properties
                }
            }
        }

        result = self.update_person(project_safe_name, source_id, updated_data)

        if result:
            return {
                "source_id": source_id,
                "target_id": target_id,
                "relationship_type": relationship_type,
                "properties": rel_props
            }
        return None

    def get_relationship(self, project_safe_name, source_id, target_id):
        """
        Get a specific relationship between two persons.

        Args:
            project_safe_name: The project's safe name
            source_id: The source person's ID
            target_id: The target person's ID

        Returns:
            Dict with relationship details or None if not found
        """
        source = self.get_person(project_safe_name, source_id)

        if not source:
            return None

        profile = source.get("profile", {})
        tagged_section = profile.get("Tagged People", {})
        tagged_ids = tagged_section.get("tagged_people", []) or []

        if target_id not in tagged_ids:
            return None

        relationship_types = tagged_section.get("relationship_types", {}) or {}
        relationship_properties = tagged_section.get("relationship_properties", {}) or {}

        rel_type = relationship_types.get(target_id, "RELATED_TO")
        rel_props = relationship_properties.get(target_id, {})

        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": rel_type,
            "properties": rel_props
        }

    def update_relationship(self, project_safe_name, source_id, target_id,
                           relationship_type=None, properties=None):
        """
        Update an existing relationship between two persons.

        Args:
            project_safe_name: The project's safe name
            source_id: The source person's ID
            target_id: The target person's ID
            relationship_type: New relationship type (optional)
            properties: Dict with properties to update (optional)

        Returns:
            Dict with updated relationship details or None if failed
        """
        source = self.get_person(project_safe_name, source_id)

        if not source:
            return None

        profile = source.get("profile", {})
        tagged_section = profile.get("Tagged People", {})
        tagged_ids = tagged_section.get("tagged_people", []) or []
        transitive = tagged_section.get("transitive_relationships", []) or []
        relationship_types = tagged_section.get("relationship_types", {}) or {}
        relationship_properties = tagged_section.get("relationship_properties", {}) or {}

        # Ensure the relationship exists
        if target_id not in tagged_ids:
            return None

        # Update relationship type if provided
        if relationship_type is not None:
            relationship_types[target_id] = relationship_type

        # Update properties if provided
        if properties is not None:
            existing_props = relationship_properties.get(target_id, {})
            if not isinstance(existing_props, dict):
                existing_props = {}
            existing_props.update(properties)
            if relationship_type is not None:
                existing_props["relationship_type"] = relationship_type
            relationship_properties[target_id] = existing_props

        # Update the person
        updated_data = {
            "profile": {
                "Tagged People": {
                    "tagged_people": tagged_ids,
                    "transitive_relationships": transitive,
                    "relationship_types": relationship_types,
                    "relationship_properties": relationship_properties
                }
            }
        }

        result = self.update_person(project_safe_name, source_id, updated_data)

        if result:
            return {
                "source_id": source_id,
                "target_id": target_id,
                "relationship_type": relationship_types.get(target_id, "RELATED_TO"),
                "properties": relationship_properties.get(target_id, {})
            }
        return None

    def delete_relationship(self, project_safe_name, source_id, target_id):
        """
        Delete a relationship between two persons.

        Args:
            project_safe_name: The project's safe name
            source_id: The source person's ID
            target_id: The target person's ID

        Returns:
            True if deleted, False otherwise
        """
        source = self.get_person(project_safe_name, source_id)

        if not source:
            return False

        profile = source.get("profile", {})
        tagged_section = profile.get("Tagged People", {})
        tagged_ids = tagged_section.get("tagged_people", []) or []
        transitive = tagged_section.get("transitive_relationships", []) or []
        relationship_types = tagged_section.get("relationship_types", {}) or {}
        relationship_properties = tagged_section.get("relationship_properties", {}) or {}

        # Ensure lists and dicts
        if not isinstance(tagged_ids, list):
            tagged_ids = [tagged_ids] if tagged_ids else []
        if not isinstance(relationship_types, dict):
            relationship_types = {}
        if not isinstance(relationship_properties, dict):
            relationship_properties = {}

        # Remove the relationship
        if target_id not in tagged_ids:
            return False

        tagged_ids.remove(target_id)
        relationship_types.pop(target_id, None)
        relationship_properties.pop(target_id, None)

        # Update the person
        updated_data = {
            "profile": {
                "Tagged People": {
                    "tagged_people": tagged_ids,
                    "transitive_relationships": transitive,
                    "relationship_types": relationship_types,
                    "relationship_properties": relationship_properties
                }
            }
        }

        result = self.update_person(project_safe_name, source_id, updated_data)
        return result is not None

    def get_all_relationships(self, project_safe_name, entity_id=None,
                             relationship_type=None, include_reverse=True):
        """
        Get all relationships in a project, optionally filtered.

        Args:
            project_safe_name: The project's safe name
            entity_id: Filter to relationships involving this entity (optional)
            relationship_type: Filter to this relationship type (optional)
            include_reverse: Include reverse relationships (default True)

        Returns:
            List of relationship dicts
        """
        people = self.get_all_people(project_safe_name)
        relationships = []

        for person in people:
            if not person:
                continue

            person_id = person.get("id")

            # Skip if we're filtering by entity and this isn't it
            if entity_id and person_id != entity_id and not include_reverse:
                continue

            profile = person.get("profile", {})
            tagged_section = profile.get("Tagged People", {})
            tagged_ids = tagged_section.get("tagged_people", []) or []
            transitive = tagged_section.get("transitive_relationships", []) or []
            rel_types = tagged_section.get("relationship_types", {}) or {}
            rel_props = tagged_section.get("relationship_properties", {}) or {}

            if not isinstance(tagged_ids, list):
                tagged_ids = [tagged_ids] if tagged_ids else []
            if not isinstance(rel_types, dict):
                rel_types = {}
            if not isinstance(rel_props, dict):
                rel_props = {}

            # Process direct relationships
            for target_id in tagged_ids:
                rel_type = rel_types.get(target_id, "RELATED_TO")
                props = rel_props.get(target_id, {})

                # Filter by entity if specified
                if entity_id and person_id != entity_id:
                    if include_reverse and target_id == entity_id:
                        pass  # Include reverse relationship
                    else:
                        continue

                # Filter by relationship type if specified
                if relationship_type and rel_type != relationship_type:
                    continue

                relationships.append({
                    "source_id": person_id,
                    "target_id": target_id,
                    "relationship_type": rel_type,
                    "properties": props,
                    "is_transitive": False
                })

            # Process transitive relationships
            for target_id in transitive:
                # Filter by entity if specified
                if entity_id and person_id != entity_id:
                    if include_reverse and target_id == entity_id:
                        pass
                    else:
                        continue

                relationships.append({
                    "source_id": person_id,
                    "target_id": target_id,
                    "relationship_type": "TRANSITIVE",
                    "properties": {},
                    "is_transitive": True
                })

        return relationships

    def get_relationship_type_counts(self, project_safe_name):
        """
        Get counts of relationships grouped by type.

        Args:
            project_safe_name: The project's safe name

        Returns:
            Dict mapping relationship types to counts
        """
        relationships = self.get_all_relationships(project_safe_name)
        counts = {}

        for rel in relationships:
            rel_type = rel.get("relationship_type", "RELATED_TO")
            counts[rel_type] = counts.get(rel_type, 0) + 1

        return counts

    def create_bidirectional_relationship(self, project_safe_name, source_id, target_id,
                                          relationship_type="RELATED_TO", properties=None):
        """
        Create a bidirectional relationship between two persons.

        For symmetric relationships (like WORKS_WITH, FRIEND), creates the same
        relationship type in both directions. For asymmetric relationships (like
        PARENT_OF), creates the inverse relationship on the target.

        Args:
            project_safe_name: The project's safe name
            source_id: The source person's ID
            target_id: The target person's ID
            relationship_type: Type of relationship
            properties: Dict with additional properties

        Returns:
            Dict with both relationship details or None if failed
        """
        # Define inverse relationship types
        inverse_types = {
            "PARENT_OF": "CHILD_OF",
            "CHILD_OF": "PARENT_OF",
            "MANAGES": "REPORTS_TO",
            "REPORTS_TO": "MANAGES",
            "EMPLOYER": "EMPLOYEE",
            "EMPLOYEE": "EMPLOYER",
        }

        # Create the forward relationship
        forward = self.create_relationship(
            project_safe_name, source_id, target_id,
            relationship_type, properties
        )

        if not forward:
            return None

        # Determine the inverse relationship type
        inverse_type = inverse_types.get(relationship_type, relationship_type)

        # Create the reverse relationship
        reverse = self.create_relationship(
            project_safe_name, target_id, source_id,
            inverse_type, properties
        )

        return {
            "forward": forward,
            "reverse": reverse
        }
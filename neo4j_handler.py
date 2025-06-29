from neo4j import GraphDatabase
import os
from datetime import datetime
from dotenv import load_dotenv
import json
from uuid import uuid4
import re

# Load environment variables from .env
load_dotenv()

class Neo4jHandler:
    def __init__(self):
        """Initialize Neo4j connection using environment variables."""
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "neo4jbasset")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
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
        """Create relationship types and properties based on the configuration."""
        with self.driver.session() as session:
            # Clear existing schema if needed
            session.run("""
                MATCH (c:Configuration {id: 'main'})
                DETACH DELETE c
            """)
            
            # Create new configuration
            session.run("""
                MERGE (config:Configuration {id: 'main'})
                SET config.updated_at = $timestamp
            """, timestamp=datetime.now().isoformat())
            
            # Process sections and fields
            for section in config.get("sections", []):
                section_id = section.get("id")
                section_label = section.get("label", section_id)
                
                session.run("""
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
                    
                    session.run("""
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
                            
                            session.run("""
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
        
    def get_all_people(self, project_safe_name):
        """Retrieve all people in a project."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(person:Person)
                RETURN person.id AS person_id
                ORDER BY person.created_at DESC
            """, project_safe_name=project_safe_name)
            
            return [self.get_person(project_safe_name, record["person_id"]) for record in result]
    
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
        """Retrieve all people in a project."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(person:Person)
                RETURN person.id AS person_id
                ORDER BY person.created_at DESC
            """, project_safe_name=project_safe_name)
            
            return [self.get_person(project_safe_name, record["person_id"]) for record in result]
    
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

    def delete_person(self, project_safe_name, person_id):
        """Delete a person and all their associated data."""
        with self.driver.session() as session:
            # First check if person exists
            verify = session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})-[:HAS_PERSON]->(person:Person {id: $person_id})
                RETURN count(person) as exists
            """, project_safe_name=project_safe_name, person_id=person_id)
            
            record = verify.single()
            if not record or record["exists"] == 0:
                return False
            
            # Delete all related data
            session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FIELD_VALUE]->(fv)
                DELETE r, fv
            """, person_id=person_id)
            
            session.run("""
                MATCH (person:Person {id: $person_id})-[r:HAS_FILE]->(file)
                DELETE r, file
            """, person_id=person_id)
            
            # Finally delete the person
            session.run("""
                MATCH (person:Person {id: $person_id})
                DETACH DELETE person
            """, person_id=person_id)
            
            return True
    
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
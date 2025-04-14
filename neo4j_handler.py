import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

class Neo4jHandler:
    def __init__(self):
        # Initialize Neo4j connection
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")

        if not neo4j_uri or not neo4j_user or not neo4j_password:
            raise ValueError("Neo4j connection details are missing in the environment variables.")

        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def close(self):
        """Close the Neo4j driver connection."""
        self.driver.close()

    def _prepare_person_data(self, person_data):
        """
        Extract and prepare nested data from the complex person JSON structure.
        Creates a flattened representation suitable for Neo4j.
        """
        # Basic properties
        neo4j_data = {
            "id": person_data["id"],
            "created_at": person_data.get("created_at")
        }
        
        # Extract key information from profile
        profile = person_data.get("profile", {})
        
        # Extract core information if available
        if "core" in profile and isinstance(profile["core"], dict):
            core_data = profile["core"]
            
            # Handle name information
            if "name" in core_data and core_data["name"]:
                name_data = core_data["name"]
                if isinstance(name_data, list) and name_data:
                    neo4j_data["first_name"] = name_data[0].get("first", "")
                    neo4j_data["last_name"] = name_data[0].get("last", "")
                    neo4j_data["display_name"] = f"{neo4j_data['first_name']} {neo4j_data['last_name']}".strip()
        
        # Store the complete profile as a JSON string for retrieval
        neo4j_data["profile_json"] = json.dumps(profile)
        
        return neo4j_data

    def _extract_profile_from_neo4j(self, neo4j_data):
        """
        Convert Neo4j data back to the application's JSON structure.
        """
        result = {
            "id": neo4j_data["id"],
            "created_at": neo4j_data.get("created_at")
        }
        
        # Parse the stored JSON profile
        if "profile_json" in neo4j_data and neo4j_data["profile_json"]:
            try:
                result["profile"] = json.loads(neo4j_data["profile_json"])
            except json.JSONDecodeError:
                result["profile"] = {}
        else:
            result["profile"] = {}
            
        return result

    def create_person(self, person_data):
        """Create a Person node in Neo4j with nested data handling."""
        prepared_data = self._prepare_person_data(person_data)
        
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Person {id: $id})
                SET p += $props
                """,
                id=prepared_data["id"],
                props=prepared_data
            )

    def get_all_people(self):
        """Get all people with fully reconstructed nested data."""
        with self.driver.session() as session:
            result = session.run("MATCH (p:Person) RETURN p")
            
            people = []
            for record in result:
                neo4j_data = dict(record["p"])
                people.append(self._extract_profile_from_neo4j(neo4j_data))
                
            return people

    def get_person_by_id(self, person_id):
        """Get a person by ID with full nested structure reconstruction."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Person {id: $id})
                RETURN p
                """,
                id=person_id
            )
            record = result.single()
            
            if not record:
                return None
                
            # Convert Neo4j node to Python dictionary
            neo4j_data = dict(record["p"])
            
            # Reconstruct the full person data
            return self._extract_profile_from_neo4j(neo4j_data)

    def update_person(self, person_id, person_data):
        """Update a Person node in Neo4j, handling nested structures."""
        prepared_data = self._prepare_person_data(person_data)
        
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Person {id: $id})
                SET p += $props
                """,
                id=person_id,
                props=prepared_data
            )

    def delete_person(self, person_id):
        """Delete a person and all their relationships."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Person {id: $id})
                DETACH DELETE p
                """,
                id=person_id
            )

    def create_relationship(self, person1_id, person2_id):
        """Create a TAGGED relationship between two people."""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p1:Person {id: $person1_id})
                MERGE (p2:Person {id: $person2_id})
                MERGE (p1)-[:TAGGED]->(p2)
                """,
                person1_id=person1_id,
                person2_id=person2_id
            )

    def tag_person(self, person_id, tagged_ids):
        """
        Create TAGGED relationships between a person and multiple other people.
        Updates the person's profile.tagged_people data.
        """
        with self.driver.session() as session:
            # First retrieve the existing person data
            person = self.get_person_by_id(person_id)
            
            if not person:
                return False
            
            # Create relationships in Neo4j
            for tagged_id in tagged_ids:
                session.run(
                    """
                    MERGE (p1:Person {id: $person_id})
                    MERGE (p2:Person {id: $tagged_id})
                    MERGE (p1)-[:TAGGED]->(p2)
                    """,
                    person_id=person_id,
                    tagged_id=tagged_id
                )
            
            # Update the tagged_people field in the profile
            if "profile" not in person:
                person["profile"] = {}
            
            if "Tagged People" not in person["profile"]:
                person["profile"]["Tagged People"] = {}
            
            person["profile"]["Tagged People"]["tagged_people"] = tagged_ids
            
            # Update the person's data in Neo4j
            self.update_person(person_id, person)
            
            return True

    def search_people(self, query):
        """
        Search for people by name or other properties in nested data.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Person)
                WHERE p.display_name CONTAINS $query 
                   OR p.first_name CONTAINS $query 
                   OR p.last_name CONTAINS $query
                RETURN p
                LIMIT 25
                """,
                query=query
            )
            
            people = []
            for record in result:
                neo4j_data = dict(record["p"])
                people.append(self._extract_profile_from_neo4j(neo4j_data))
                
            return people
        
    def get_connections(self, person_id, max_hops=2):
        """
        Get all connections up to a certain number of hops.
        Returns people connected to the specified person within max_hops.
        """
        with self.driver.session() as session:
            # This query finds all connections in both directions
            result = session.run(
                """
                MATCH path = (p:Person {id: $person_id})-[:TAGGED*1..$max_hops]-(connected:Person)
                WITH connected, min(length(path)) AS hops
                RETURN connected.id AS connection_id, hops
                ORDER BY hops
                """,
                person_id=person_id,
                max_hops=max_hops
            )
            return [{"id": record["connection_id"], "hops": record["hops"]} 
                    for record in result]
        
    def get_connections_with_details(self, person_id, max_hops=2):
        """
        Get all connections up to a certain number of hops with full person details.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = (p:Person {id: $person_id})-[:TAGGED*1..$max_hops]-(connected:Person)
                WITH connected, min(length(path)) AS hops
                RETURN connected, hops
                ORDER BY hops
                """,
                person_id=person_id,
                max_hops=max_hops
            )
            
            connections = []
            for record in result:
                neo4j_data = dict(record["connected"])
                person_data = self._extract_profile_from_neo4j(neo4j_data)
                connections.append({
                    "person": person_data,
                    "hops": record["hops"]
                })
                
            return connections
            
    def get_full_graph(self):
        """Get all nodes and relationships in the graph."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p1:Person)-[r:TAGGED]->(p2:Person)
                RETURN p1.id AS source, p2.id AS target
                """
            )
            return [{"source": record["source"], "target": record["target"]} for record in result]
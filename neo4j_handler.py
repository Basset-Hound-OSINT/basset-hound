import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables from .env file
load_dotenv()

class Neo4jHandler:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

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

    def get_connections(self, person_id, max_hops=2):
        """Get all connections up to a certain number of hops."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Person {id: $person_id})-[:TAGGED*1..$max_hops]-(connected)
                RETURN DISTINCT connected.id AS connection_id
                """,
                person_id=person_id,
                max_hops=max_hops
            )
            return [record["connection_id"] for record in result]

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
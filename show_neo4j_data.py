#!/usr/bin/env python3
"""
Neo4j Database Inspector
Prints all information from a Neo4j database in a nice format.
"""

import os
import time
from neo4j import GraphDatabase
from dotenv import load_dotenv
from collections import defaultdict
import json

# Load environment variables
load_dotenv()

class Neo4jInspector:
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

    def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            self.driver.close()

    def get_database_info(self):
        """Get basic database information."""
        with self.driver.session() as session:
            # Get node count
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            node_count = result.single()["node_count"]
            
            # Get relationship count
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
            rel_count = result.single()["rel_count"]
            
            # Get node labels
            result = session.run("CALL db.labels()")
            labels = [record["label"] for record in result]
            
            # Get relationship types
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in result]
            
            return {
                "node_count": node_count,
                "relationship_count": rel_count,
                "labels": labels,
                "relationship_types": rel_types
            }

    def get_nodes_by_label(self, label):
        """Get all nodes with a specific label."""
        with self.driver.session() as session:
            query = f"MATCH (n:{label}) RETURN n LIMIT 1000"
            result = session.run(query)
            return [dict(record["n"]) for record in result]

    def get_relationships_by_type(self, rel_type):
        """Get all relationships of a specific type."""
        with self.driver.session() as session:
            query = f"MATCH (a)-[r:{rel_type}]->(b) RETURN a, r, b LIMIT 1000"
            result = session.run(query)
            relationships = []
            for record in result:
                relationships.append({
                    "start_node": dict(record["a"]),
                    "relationship": dict(record["r"]),
                    "end_node": dict(record["b"])
                })
            return relationships

    def get_schema_info(self):
        """Get schema information including indexes and constraints."""
        schema_info = {}
        
        with self.driver.session() as session:
            # Get indexes
            try:
                result = session.run("CALL db.indexes()")
                schema_info["indexes"] = [dict(record) for record in result]
            except:
                schema_info["indexes"] = []
            
            # Get constraints
            try:
                result = session.run("CALL db.constraints()")
                schema_info["constraints"] = [dict(record) for record in result]
            except:
                schema_info["constraints"] = []
        
        return schema_info

    def print_separator(self, title, char="=", width=80):
        """Print a formatted separator."""
        print(f"\n{char * width}")
        print(f"{title.upper().center(width)}")
        print(f"{char * width}")

    def print_subsection(self, title, char="-", width=60):
        """Print a formatted subsection."""
        print(f"\n{char * width}")
        print(f" {title}")
        print(f"{char * width}")

    def format_dict(self, data, indent=2):
        """Format a dictionary for pretty printing."""
        if not data:
            return "  No data"
        
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{' ' * indent}{key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"{' ' * (indent + 2)}{sub_key}: {sub_value}")
            elif isinstance(value, list):
                if value:
                    lines.append(f"{' ' * indent}{key}: {', '.join(map(str, value))}")
                else:
                    lines.append(f"{' ' * indent}{key}: []")
            else:
                lines.append(f"{' ' * indent}{key}: {value}")
        return '\n'.join(lines)

    def inspect_database(self):
        """Main method to inspect and print database information."""
        try:
            self.print_separator("Neo4j Database Inspection Report")
            
            # Get basic database info
            db_info = self.get_database_info()
            
            print(f"\nDatabase URI: {self.uri}")
            print(f"Total Nodes: {db_info['node_count']:,}")
            print(f"Total Relationships: {db_info['relationship_count']:,}")
            print(f"Node Labels: {len(db_info['labels'])}")
            print(f"Relationship Types: {len(db_info['relationship_types'])}")

            # Print schema information
            self.print_separator("Schema Information")
            schema_info = self.get_schema_info()
            
            if schema_info["indexes"]:
                self.print_subsection("Indexes")
                for idx in schema_info["indexes"]:
                    print(f"  • {idx.get('name', 'N/A')} - {idx.get('description', 'N/A')}")
            
            if schema_info["constraints"]:
                self.print_subsection("Constraints")
                for constraint in schema_info["constraints"]:
                    print(f"  • {constraint.get('name', 'N/A')} - {constraint.get('description', 'N/A')}")

            # Print node information by label
            self.print_separator("Nodes by Label")
            
            for label in db_info['labels']:
                nodes = self.get_nodes_by_label(label)
                self.print_subsection(f"Label: {label} ({len(nodes)} nodes)")
                
                if nodes:
                    # Show first few nodes as examples
                    for i, node in enumerate(nodes[:3]):  # Show first 3 nodes
                        print(f"\n  Node {i+1}:")
                        print(self.format_dict(node, 4))
                    
                    if len(nodes) > 3:
                        print(f"\n  ... and {len(nodes) - 3} more nodes")
                        
                    # Show property summary
                    all_properties = set()
                    for node in nodes:
                        all_properties.update(node.keys())
                    
                    if all_properties:
                        print(f"\n  Properties found: {', '.join(sorted(all_properties))}")

            # Print relationship information by type
            if db_info['relationship_types']:
                self.print_separator("Relationships by Type")
                
                for rel_type in db_info['relationship_types']:
                    relationships = self.get_relationships_by_type(rel_type)
                    self.print_subsection(f"Relationship: {rel_type} ({len(relationships)} relationships)")
                    
                    if relationships:
                        # Show first few relationships as examples
                        for i, rel in enumerate(relationships[:2]):  # Show first 2 relationships
                            print(f"\n  Relationship {i+1}:")
                            print(f"    Start Node: {self.format_dict(rel['start_node'], 6).strip()}")
                            if rel['relationship']:
                                print(f"    Relationship Properties: {self.format_dict(rel['relationship'], 6).strip()}")
                            print(f"    End Node: {self.format_dict(rel['end_node'], 6).strip()}")
                        
                        if len(relationships) > 2:
                            print(f"\n  ... and {len(relationships) - 2} more relationships")

            self.print_separator("Inspection Complete")
            print("Database inspection finished successfully!")

        except Exception as e:
            print(f"Error during database inspection: {e}")
            raise

def main():
    """Main function to run the database inspection."""
    inspector = None
    try:
        print("Starting Neo4j Database Inspection...")
        inspector = Neo4jInspector()
        inspector.inspect_database()
    except Exception as e:
        print(f"Failed to inspect database: {e}")
    finally:
        if inspector:
            inspector.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()
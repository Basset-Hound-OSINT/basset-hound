"""
Graph Visualization Service for Basset Hound.

This service provides methods to fetch and format graph data for various
frontend visualization libraries (D3.js, vis.js, Cytoscape).
"""

from typing import Dict, List, Any, Optional, Literal
import logging

logger = logging.getLogger("basset_hound.graph_service")


class GraphService:
    """Service for graph data retrieval and format conversion."""

    def __init__(self, neo4j_handler):
        """
        Initialize the graph service.

        Args:
            neo4j_handler: Neo4j database handler instance
        """
        self.neo4j = neo4j_handler

    def get_project_graph(
        self,
        project_safe_name: str,
        include_orphans: bool = True
    ) -> Dict[str, Any]:
        """
        Get the complete graph for a project.

        Args:
            project_safe_name: The project's safe name
            include_orphans: Whether to include entities with no relationships

        Returns:
            Dict with 'nodes' and 'edges' lists containing raw graph data
        """
        with self.neo4j.driver.session() as session:
            # Get all entities in the project
            entities_query = """
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person)
                RETURN person.id AS id, person.profile AS profile,
                       person.created_at AS created_at
                ORDER BY person.created_at DESC
            """
            entities_result = session.run(
                entities_query,
                project_safe_name=project_safe_name
            )

            nodes = []
            entity_ids = set()

            for record in entities_result:
                entity_id = record["id"]
                entity_ids.add(entity_id)

                profile = record["profile"] or {}

                # Extract display name from profile
                display_name = self._extract_display_name(profile, entity_id)

                nodes.append({
                    "id": entity_id,
                    "label": display_name,
                    "type": "Person",
                    "properties": {
                        "profile": profile,
                        "created_at": record["created_at"]
                    }
                })

            # Get all relationships between entities
            edges = []

            for node in nodes:
                entity_id = node["id"]
                profile = node["properties"]["profile"]
                tagged_section = profile.get("Tagged People", {})

                tagged_ids = tagged_section.get("tagged_people", []) or []
                if not isinstance(tagged_ids, list):
                    tagged_ids = [tagged_ids] if tagged_ids else []

                relationship_types = tagged_section.get("relationship_types", {}) or {}
                relationship_properties = tagged_section.get("relationship_properties", {}) or {}

                for target_id in tagged_ids:
                    # Only include if target exists in this project
                    if target_id in entity_ids:
                        rel_type = relationship_types.get(target_id, "RELATED_TO")
                        rel_props = relationship_properties.get(target_id, {})

                        edges.append({
                            "source": entity_id,
                            "target": target_id,
                            "type": rel_type,
                            "properties": rel_props
                        })

            # Filter orphans if needed
            if not include_orphans:
                connected_ids = set()
                for edge in edges:
                    connected_ids.add(edge["source"])
                    connected_ids.add(edge["target"])

                nodes = [n for n in nodes if n["id"] in connected_ids]

            return {
                "nodes": nodes,
                "edges": edges
            }

    def get_entity_subgraph(
        self,
        project_safe_name: str,
        entity_id: str,
        depth: int = 2,
        include_orphans: bool = False
    ) -> Dict[str, Any]:
        """
        Get a subgraph centered around a specific entity.

        Args:
            project_safe_name: The project's safe name
            entity_id: The entity to center the subgraph around
            depth: Number of relationship hops to include (default: 2)
            include_orphans: Whether to include entities with no relationships

        Returns:
            Dict with 'nodes' and 'edges' lists containing raw graph data
        """
        # Verify entity exists
        entity = self.neo4j.get_person(project_safe_name, entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found in project {project_safe_name}")

        # Get full project graph first
        full_graph = self.get_project_graph(project_safe_name, include_orphans=True)

        # Build adjacency list for traversal
        adjacency = {}
        for edge in full_graph["edges"]:
            source = edge["source"]
            target = edge["target"]

            if source not in adjacency:
                adjacency[source] = []
            if target not in adjacency:
                adjacency[target] = []

            adjacency[source].append(target)
            adjacency[target].append(source)

        # BFS to find entities within depth
        visited = {entity_id}
        current_level = {entity_id}

        for _ in range(depth):
            next_level = set()
            for node_id in current_level:
                neighbors = adjacency.get(node_id, [])
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.add(neighbor)
            current_level = next_level
            if not current_level:
                break

        # Filter nodes and edges to subgraph
        nodes = [n for n in full_graph["nodes"] if n["id"] in visited]
        edges = [
            e for e in full_graph["edges"]
            if e["source"] in visited and e["target"] in visited
        ]

        # Filter orphans if needed
        if not include_orphans:
            connected_ids = set()
            for edge in edges:
                connected_ids.add(edge["source"])
                connected_ids.add(edge["target"])

            nodes = [n for n in nodes if n["id"] in connected_ids]

        return {
            "nodes": nodes,
            "edges": edges,
            "center_entity": entity_id,
            "depth": depth
        }

    def get_cluster_graph(
        self,
        project_safe_name: str,
        cluster_id: str
    ) -> Dict[str, Any]:
        """
        Get the graph for a specific cluster.

        Args:
            project_safe_name: The project's safe name
            cluster_id: The cluster root entity ID

        Returns:
            Dict with 'nodes' and 'edges' lists containing raw graph data
        """
        # Get all clusters
        clusters_data = self.neo4j.get_clusters(project_safe_name)

        # Find the specific cluster
        target_cluster = None
        for cluster in clusters_data.get("clusters", []):
            if cluster["cluster_id"] == cluster_id:
                target_cluster = cluster
                break

        if not target_cluster:
            raise ValueError(f"Cluster {cluster_id} not found in project {project_safe_name}")

        cluster_entity_ids = set(target_cluster["entity_ids"])

        # Get full project graph
        full_graph = self.get_project_graph(project_safe_name, include_orphans=True)

        # Filter to cluster entities
        nodes = [n for n in full_graph["nodes"] if n["id"] in cluster_entity_ids]
        edges = [
            e for e in full_graph["edges"]
            if e["source"] in cluster_entity_ids and e["target"] in cluster_entity_ids
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "cluster_id": cluster_id,
            "cluster_size": target_cluster["size"],
            "is_isolated": target_cluster["is_isolated"]
        }

    def format_for_d3(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format graph data for D3.js.

        Args:
            graph_data: Raw graph data with 'nodes' and 'edges'

        Returns:
            Dict in D3.js format with 'nodes' and 'links'
        """
        nodes = []
        for node in graph_data["nodes"]:
            nodes.append({
                "id": node["id"],
                "label": node["label"],
                "type": node["type"],
                "properties": node["properties"]
            })

        links = []
        for edge in graph_data["edges"]:
            links.append({
                "source": edge["source"],
                "target": edge["target"],
                "type": edge["type"],
                "properties": edge.get("properties", {})
            })

        result = {
            "nodes": nodes,
            "links": links
        }

        # Include metadata if present
        for key in ["center_entity", "depth", "cluster_id", "cluster_size", "is_isolated"]:
            if key in graph_data:
                result[key] = graph_data[key]

        return result

    def format_for_vis(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format graph data for vis.js.

        Args:
            graph_data: Raw graph data with 'nodes' and 'edges'

        Returns:
            Dict in vis.js format with 'nodes' and 'edges'
        """
        nodes = []
        for node in graph_data["nodes"]:
            # Create tooltip with profile info
            profile = node["properties"].get("profile", {})
            title_parts = [node["label"]]

            # Add some profile fields to tooltip
            if "profile" in profile:
                for key, value in profile["profile"].items():
                    if value and key not in ["id", "created_at"]:
                        title_parts.append(f"{key}: {value}")

            nodes.append({
                "id": node["id"],
                "label": node["label"],
                "group": node["type"],
                "title": "<br>".join(title_parts),
                "value": 1  # Size can be adjusted based on connections
            })

        edges = []
        edge_id = 0
        for edge in graph_data["edges"]:
            edge_label = edge["type"].replace("_", " ").title()

            # Add confidence to label if present
            props = edge.get("properties", {})
            if "confidence" in props:
                edge_label += f" ({props['confidence']})"

            edges.append({
                "id": edge_id,
                "from": edge["source"],
                "to": edge["target"],
                "label": edge_label,
                "arrows": "to",
                "title": f"{edge['type']}"
            })
            edge_id += 1

        result = {
            "nodes": nodes,
            "edges": edges
        }

        # Include metadata if present
        for key in ["center_entity", "depth", "cluster_id", "cluster_size", "is_isolated"]:
            if key in graph_data:
                result[key] = graph_data[key]

        return result

    def format_for_cytoscape(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format graph data for Cytoscape.js.

        Args:
            graph_data: Raw graph data with 'nodes' and 'edges'

        Returns:
            Dict in Cytoscape.js format with 'elements'
        """
        elements = {
            "nodes": [],
            "edges": []
        }

        for node in graph_data["nodes"]:
            elements["nodes"].append({
                "data": {
                    "id": node["id"],
                    "label": node["label"],
                    "type": node["type"],
                    "properties": node["properties"]
                }
            })

        edge_id = 0
        for edge in graph_data["edges"]:
            elements["edges"].append({
                "data": {
                    "id": f"edge_{edge_id}",
                    "source": edge["source"],
                    "target": edge["target"],
                    "label": edge["type"],
                    "type": edge["type"],
                    "properties": edge.get("properties", {})
                }
            })
            edge_id += 1

        result = {"elements": elements}

        # Include metadata if present
        for key in ["center_entity", "depth", "cluster_id", "cluster_size", "is_isolated"]:
            if key in graph_data:
                result[key] = graph_data[key]

        return result

    def _extract_display_name(self, profile: Dict[str, Any], entity_id: str) -> str:
        """
        Extract a display name from entity profile.

        Args:
            profile: Entity profile dict
            entity_id: Entity ID (fallback)

        Returns:
            Display name string
        """
        # Try to get name from profile section
        if "profile" in profile:
            profile_section = profile["profile"]

            # Try first_name + last_name
            first_name = profile_section.get("first_name", "")
            last_name = profile_section.get("last_name", "")

            if first_name or last_name:
                return f"{first_name} {last_name}".strip()

            # Try full_name
            if "full_name" in profile_section:
                return profile_section["full_name"]

            # Try name
            if "name" in profile_section:
                return profile_section["name"]

        # Try other common fields
        for section in profile.values():
            if isinstance(section, dict):
                if "username" in section:
                    return f"@{section['username']}"
                if "email" in section:
                    return section["email"].split("@")[0]

        # Fallback to entity ID (shortened)
        return f"Entity {entity_id[:8]}"


def get_graph_service(neo4j_handler) -> GraphService:
    """
    Factory function to create a GraphService instance.

    Args:
        neo4j_handler: Neo4j database handler

    Returns:
        GraphService instance
    """
    return GraphService(neo4j_handler)

"""
Graph analysis tools for MCP.

Provides tools for analyzing the entity relationship graph,
including path finding, centrality analysis, and cluster detection.
"""

from .base import get_neo4j_handler, get_project_safe_name


def register_analysis_tools(mcp):
    """Register graph analysis tools with the MCP server."""

    @mcp.tool()
    def find_path(project_id: str, entity_id_1: str, entity_id_2: str, find_all: bool = False, max_depth: int = 5) -> dict:
        """
        Find path(s) between two entities in the relationship graph.

        Uses graph traversal to find connections between entities through
        their tagged relationships. Can find either the shortest path or
        all paths up to a maximum depth.

        Args:
            project_id: The project ID or safe_name
            entity_id_1: The starting entity ID
            entity_id_2: The target entity ID
            find_all: If True, find all paths; if False, find only shortest path (default: False)
            max_depth: Maximum path depth when finding all paths (default: 5)

        Returns:
            Dictionary with path information:
            - For shortest path: found, path_length, entity_ids, entities
            - For all paths: found, path_count, paths (list of path info)
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Verify both entities exist
        entity1 = handler.get_person(safe_name, entity_id_1)
        entity2 = handler.get_person(safe_name, entity_id_2)

        if not entity1:
            return {"error": f"Entity not found: {entity_id_1}"}
        if not entity2:
            return {"error": f"Entity not found: {entity_id_2}"}

        if find_all:
            result = handler.find_all_paths(safe_name, entity_id_1, entity_id_2, max_depth)
        else:
            result = handler.find_shortest_path(safe_name, entity_id_1, entity_id_2)

        if result is None:
            return {"error": "Failed to find path - entities may not exist in the project"}

        return result

    @mcp.tool()
    def analyze_connections(project_id: str, entity_id: str = None, top_n: int = 10) -> dict:
        """
        Analyze connection patterns and centrality in the entity graph.

        If entity_id is provided, returns detailed centrality metrics for that entity.
        If entity_id is not provided, returns the most connected entities in the project.

        Args:
            project_id: The project ID or safe_name
            entity_id: Optional entity ID to analyze (if None, returns most connected entities)
            top_n: Number of most connected entities to return (default: 10)

        Returns:
            For specific entity: degree centrality, incoming/outgoing connections, normalized score
            For project-wide: list of most connected entities with connection counts
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if entity_id:
            # Get centrality for specific entity
            result = handler.get_entity_centrality(safe_name, entity_id)
            if result is None:
                return {"error": f"Entity not found: {entity_id}"}
            return result
        else:
            # Get most connected entities
            result = handler.get_most_connected(safe_name, limit=top_n)
            return result

    @mcp.tool()
    def get_network_clusters(project_id: str, include_isolated: bool = True) -> dict:
        """
        Detect and return connected components (clusters) in the entity network.

        Identifies groups of entities that are connected to each other through
        relationships but not connected to entities in other groups. Useful for
        finding distinct networks or communities within a project.

        Args:
            project_id: The project ID or safe_name
            include_isolated: Whether to include isolated entities (no connections) as single-entity clusters (default: True)

        Returns:
            Dictionary with:
            - cluster_count: Total number of clusters
            - connected_clusters: Number of clusters with 2+ entities
            - isolated_count: Number of entities with no connections
            - clusters: List of cluster details (size, members, internal edges)
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        result = handler.find_clusters(safe_name)

        if not include_isolated:
            # Filter out isolated entities
            result["clusters"] = [c for c in result["clusters"] if not c["is_isolated"]]
            result["cluster_count"] = len(result["clusters"])

        return result

    @mcp.tool()
    def get_entity_network(project_id: str, entity_id: str, depth: int = 2) -> dict:
        """
        Get the neighborhood network around a specific entity.

        Returns all entities within N hops of the specified entity,
        creating an ego network useful for understanding an entity's
        local connections and influence.

        Args:
            project_id: The project ID or safe_name
            entity_id: The center entity ID
            depth: Maximum number of hops from the center entity (default: 2)

        Returns:
            Dictionary with:
            - center_entity_id: The specified entity
            - total_entities: Count of entities in the neighborhood
            - neighborhood: Entities organized by distance (depth_0, depth_1, etc.)
            - edges: List of connections within the neighborhood
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        result = handler.get_entity_neighborhood(safe_name, entity_id, depth)

        if result is None:
            return {"error": f"Entity not found: {entity_id}"}

        return result

    @mcp.tool()
    def get_entity_graph(
        project_id: str,
        entity_ids: list = None,
        include_orphans: bool = False,
        format: str = "standard"
    ) -> dict:
        """
        Export the complete entity relationship graph or a subgraph.

        Returns a graph representation suitable for visualization tools,
        analysis libraries, or AI agent consumption.

        Args:
            project_id: The project ID or safe_name
            entity_ids: Optional list of entity IDs to include (None = all entities)
            include_orphans: Whether to include orphan data nodes (default: False)
            format: Output format - "standard" (nodes/edges), "adjacency" (adjacency list),
                   "cytoscape" (Cytoscape.js format) (default: "standard")

        Returns:
            Graph data in specified format with nodes, edges, and metadata
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Get entities
        all_entities = handler.get_all_people(safe_name)

        if entity_ids:
            entities = [e for e in all_entities if e.get("id") in entity_ids]
            if not entities:
                return {"error": "No matching entities found"}
        else:
            entities = all_entities

        # Build node list
        nodes = []
        entity_id_set = set()
        for entity in entities:
            entity_id = entity.get("id")
            entity_id_set.add(entity_id)

            # Extract display name from profile
            profile = entity.get("profile", {})
            core = profile.get("core", {})
            name_data = core.get("name", [])

            if name_data and isinstance(name_data, list) and len(name_data) > 0:
                first_name = name_data[0]
                if isinstance(first_name, dict):
                    display_name = " ".join(filter(None, [
                        first_name.get("first_name", ""),
                        first_name.get("last_name", "")
                    ])) or entity_id[:8]
                else:
                    display_name = str(first_name)
            else:
                display_name = entity_id[:8]

            nodes.append({
                "id": entity_id,
                "type": "entity",
                "label": display_name,
                "created_at": entity.get("created_at"),
                "section_count": len([s for s in profile.keys() if not s.startswith("_")])
            })

        # Build edges from relationships
        edges = []
        edge_set = set()  # Avoid duplicates

        for entity in entities:
            entity_id = entity.get("id")
            profile = entity.get("profile", {})
            tagged = profile.get("Tagged People", {})

            if tagged and isinstance(tagged, dict):
                relationships = tagged.get("relationships", [])
                if isinstance(relationships, list):
                    for rel in relationships:
                        if isinstance(rel, dict):
                            target_id = rel.get("target_entity_id")
                            if target_id and target_id in entity_id_set:
                                # Create unique edge key (sorted to handle bidirectional)
                                edge_key = tuple(sorted([entity_id, target_id])) + (rel.get("type", "RELATED"),)
                                if edge_key not in edge_set:
                                    edge_set.add(edge_key)
                                    edges.append({
                                        "source": entity_id,
                                        "target": target_id,
                                        "type": rel.get("type", "RELATED"),
                                        "confidence": rel.get("confidence", "medium"),
                                        "bidirectional": rel.get("bidirectional", False)
                                    })

        # Optionally include orphans
        orphan_nodes = []
        orphan_edges = []
        if include_orphans:
            orphans = handler.list_orphan_data(safe_name, filters={"linked": True})
            for orphan in orphans:
                orphan_id = orphan.get("id")
                orphan_nodes.append({
                    "id": orphan_id,
                    "type": "orphan",
                    "label": f"{orphan.get('identifier_type', 'unknown')}: {orphan.get('identifier_value', '')[:20]}",
                    "identifier_type": orphan.get("identifier_type"),
                    "identifier_value": orphan.get("identifier_value")
                })

                # Add edge to linked entity
                linked_entity_id = orphan.get("linked_entity_id")
                if linked_entity_id and linked_entity_id in entity_id_set:
                    orphan_edges.append({
                        "source": orphan_id,
                        "target": linked_entity_id,
                        "type": "LINKED_TO"
                    })

            nodes.extend(orphan_nodes)
            edges.extend(orphan_edges)

        # Format output
        if format == "adjacency":
            # Adjacency list format
            adjacency = {}
            for node in nodes:
                adjacency[node["id"]] = []

            for edge in edges:
                adjacency[edge["source"]].append({
                    "target": edge["target"],
                    "type": edge["type"]
                })
                # Add reverse for bidirectional
                if edge.get("bidirectional"):
                    adjacency[edge["target"]].append({
                        "target": edge["source"],
                        "type": edge["type"]
                    })

            return {
                "project_id": project_id,
                "format": "adjacency",
                "node_count": len(nodes),
                "edge_count": len(edges),
                "nodes": {n["id"]: {"label": n["label"], "type": n["type"]} for n in nodes},
                "adjacency": adjacency
            }

        elif format == "cytoscape":
            # Cytoscape.js format
            cyto_nodes = [{"data": node} for node in nodes]
            cyto_edges = [{"data": {**edge, "id": f"{edge['source']}-{edge['target']}"}} for edge in edges]

            return {
                "project_id": project_id,
                "format": "cytoscape",
                "elements": {
                    "nodes": cyto_nodes,
                    "edges": cyto_edges
                }
            }

        else:
            # Standard format
            return {
                "project_id": project_id,
                "format": "standard",
                "node_count": len(nodes),
                "edge_count": len(edges),
                "entity_count": len([n for n in nodes if n["type"] == "entity"]),
                "orphan_count": len([n for n in nodes if n["type"] == "orphan"]),
                "nodes": nodes,
                "edges": edges
            }

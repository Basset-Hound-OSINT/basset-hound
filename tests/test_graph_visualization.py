#!/usr/bin/env python3
"""
Test script for Graph Visualization in Basset Hound
Tests map.html with live API data
"""

import requests
import time
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8080"
API_BASE = f"{BASE_URL}/api/v1"

def log(msg, level="INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {msg}")

def check_health():
    """Check if API is healthy"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        log(f"Health check: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        log(f"Health check failed: {e}", "ERROR")
        return False

def wait_for_api(max_retries=30, delay=2):
    """Wait for API to become available"""
    for i in range(max_retries):
        if check_health():
            log("API is healthy")
            return True
        log(f"Waiting for API... ({i+1}/{max_retries})")
        time.sleep(delay)
    return False

def create_test_project():
    """Create a test project"""
    try:
        response = requests.post(
            f"{API_BASE}/projects",
            json={
                "name": "test-graph-viz",
                "description": "Test project for graph visualization"
            },
            timeout=10
        )
        if response.status_code in [200, 201]:
            project = response.json()
            log(f"Created project: {project}")
            return project
        else:
            log(f"Failed to create project: {response.status_code} - {response.text}", "ERROR")
            return None
    except Exception as e:
        log(f"Error creating project: {e}", "ERROR")
        return None

def create_test_entities(project_name, count=15):
    """Create test entities (people)"""
    entities = []
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry", "Iris", "Jack",
                   "Karen", "Leo", "Mia", "Noah", "Olivia"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]

    for i in range(min(count, len(first_names))):
        try:
            entity_data = {
                "profile": {
                    "core": {
                        "name": [
                            {
                                "first_name": first_names[i],
                                "last_name": last_names[i]
                            }
                        ],
                        "email": [f"{first_names[i].lower()}.{last_names[i].lower()}@example.com"]
                    }
                }
            }
            response = requests.post(
                f"{API_BASE}/projects/{project_name}/people",
                json=entity_data,
                timeout=10
            )
            if response.status_code in [200, 201]:
                entity = response.json()
                entities.append(entity)
                log(f"Created entity: {first_names[i]} {last_names[i]} (ID: {entity.get('id', 'unknown')[:8]})")
            else:
                log(f"Failed to create entity: {response.status_code}", "WARNING")
        except Exception as e:
            log(f"Error creating entity: {e}", "WARNING")

    return entities

def create_relationships(project_name, entities):
    """Create relationships between entities"""
    if len(entities) < 2:
        log("Not enough entities to create relationships", "WARNING")
        return []

    relationships = [
        ("KNOWS", 0, 1),
        ("WORKS_WITH", 1, 2),
        ("WORKS_WITH", 2, 3),
        ("KNOWS", 3, 4),
        ("KNOWS", 4, 5),
        ("WORKS_WITH", 5, 6),
        ("KNOWS", 6, 7),
        ("WORKS_WITH", 7, 8),
        ("KNOWS", 8, 0),
        ("WORKS_WITH", 0, 9),
        ("KNOWS", 9, 10),
        ("WORKS_WITH", 10, 11),
        ("KNOWS", 11, 12),
        ("WORKS_WITH", 12, 13),
        ("KNOWS", 13, 14),
    ]

    created = []
    for rel_type, src_idx, tgt_idx in relationships:
        if src_idx >= len(entities) or tgt_idx >= len(entities):
            continue

        source_id = entities[src_idx].get("id")
        target_id = entities[tgt_idx].get("id")

        if not source_id or not target_id:
            continue

        try:
            # Tag the source entity with target entity
            tag_data = {
                "type": rel_type,
                "target_id": target_id,
                "confidence": "high" if rel_type == "WORKS_WITH" else "medium"
            }
            response = requests.post(
                f"{API_BASE}/projects/{project_name}/people/{source_id}/tags",
                json=tag_data,
                timeout=10
            )
            if response.status_code in [200, 201]:
                log(f"Created {rel_type} relationship: {source_id[:8]} -> {target_id[:8]}")
                created.append((source_id, target_id, rel_type))
            else:
                log(f"Failed to create relationship: {response.status_code}", "WARNING")
        except Exception as e:
            log(f"Error creating relationship: {e}", "WARNING")

    return created

def test_graph_endpoints(project_name, entity_id):
    """Test graph visualization endpoints"""
    results = {}

    # Test 1: Get project graph
    log("Testing: GET /api/v1/projects/{project}/graph/entity/{entity_id}")
    try:
        response = requests.get(
            f"{API_BASE}/projects/{project_name}/graph/entity/{entity_id}",
            params={"format": "cytoscape", "depth": 2},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            results["graph_endpoint"] = "PASS"
            nodes = data.get("elements", {}).get("nodes", [])
            edges = data.get("elements", {}).get("edges", [])
            log(f"Graph data retrieved: {len(nodes)} nodes, {len(edges)} edges")
        else:
            results["graph_endpoint"] = f"FAIL ({response.status_code})"
            log(f"Graph endpoint failed: {response.status_code}", "ERROR")
    except Exception as e:
        results["graph_endpoint"] = f"ERROR: {str(e)}"
        log(f"Graph endpoint error: {e}", "ERROR")

    # Test 2: Test different depths
    log("Testing: Depth parameter (1-5)")
    try:
        for depth in [1, 2, 3, 4, 5]:
            response = requests.get(
                f"{API_BASE}/projects/{project_name}/graph/entity/{entity_id}",
                params={"format": "cytoscape", "depth": depth},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                nodes = data.get("elements", {}).get("nodes", [])
                log(f"Depth {depth}: {len(nodes)} nodes")
            else:
                log(f"Depth {depth} failed", "WARNING")
    except Exception as e:
        log(f"Depth test error: {e}", "WARNING")

    # Test 3: Test export endpoint
    log("Testing: POST /api/v1/projects/{project}/visualization/export/{format}")
    try:
        response = requests.post(
            f"{API_BASE}/projects/{project_name}/visualization/export/graphml",
            timeout=10
        )
        if response.status_code == 200:
            results["export_endpoint"] = "PASS"
            log(f"Export successful: {len(response.content)} bytes")
        else:
            results["export_endpoint"] = f"FAIL ({response.status_code})"
            log(f"Export failed: {response.status_code}", "ERROR")
    except Exception as e:
        results["export_endpoint"] = f"ERROR: {str(e)}"
        log(f"Export error: {e}", "ERROR")

    # Test 4: Test visualization graph endpoint
    log("Testing: GET /api/v1/projects/{project}/visualization/graph")
    try:
        response = requests.get(
            f"{API_BASE}/projects/{project_name}/visualization/graph",
            timeout=10
        )
        if response.status_code == 200:
            results["viz_graph_endpoint"] = "PASS"
            data = response.json()
            log(f"Visualization graph retrieved successfully")
        else:
            results["viz_graph_endpoint"] = f"FAIL ({response.status_code})"
            log(f"Visualization graph failed: {response.status_code}", "WARNING")
    except Exception as e:
        results["viz_graph_endpoint"] = f"ERROR: {str(e)}"
        log(f"Visualization graph error: {e}", "WARNING")

    return results

def main():
    """Main test function"""
    log("Starting Graph Visualization Tests")
    log(f"Target: {BASE_URL}")

    # Wait for API
    log("Waiting for API to be available...")
    if not wait_for_api():
        log("API did not become available", "ERROR")
        return False

    # Create test project
    log("\n=== Creating Test Project ===")
    project = create_test_project()
    if not project:
        log("Failed to create test project", "ERROR")
        return False

    project_name = project.get("safe_name", "test-graph-viz")
    log(f"Using project: {project_name}")

    # Create test entities
    log("\n=== Creating Test Entities ===")
    entities = create_test_entities(project_name, count=15)
    if not entities:
        log("Failed to create test entities", "ERROR")
        return False

    log(f"Created {len(entities)} entities")

    # Create relationships
    log("\n=== Creating Relationships ===")
    relationships = create_relationships(project_name, entities)
    log(f"Created {len(relationships)} relationships")

    # Test endpoints
    log("\n=== Testing Graph Visualization Endpoints ===")
    if entities:
        test_results = test_graph_endpoints(project_name, entities[0].get("id"))

        log("\n=== Test Results ===")
        for test_name, result in test_results.items():
            status = "PASS" if "PASS" in result else "FAIL"
            log(f"{test_name}: {result}", "INFO" if "PASS" in result else "WARNING")

    # Summary
    log("\n=== Test Complete ===")
    log(f"Access the graph visualization at:")
    log(f"  {BASE_URL}/map.html?project={project_name}&personId={entities[0].get('id')}&depth=2")

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("\nTest interrupted", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error: {e}", "ERROR")
        sys.exit(1)

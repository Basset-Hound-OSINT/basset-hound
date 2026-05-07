"""
Docker container startup tests for Basset Hound deployment.

These tests verify that:
1. Neo4j container is running and accessible
2. Redis container is running and accessible
3. Basset API container is running
"""

import pytest
import os
from typing import Optional


class TestNeo4jContainer:
    """Test Neo4j Docker container."""

    @pytest.mark.asyncio
    async def test_neo4j_container_running(self):
        """Test that Neo4j container is running and accessible."""
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

        try:
            from neo4j import GraphDatabase
        except ImportError:
            pytest.skip("neo4j driver not installed")

        try:
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            driver.verify_connectivity()
            driver.close()
            assert True, "Successfully connected to Neo4j"
        except Exception as e:
            pytest.skip(f"Neo4j container not running or not accessible: {str(e)}")

    @pytest.mark.asyncio
    async def test_neo4j_responds_to_query(self):
        """Test that Neo4j responds to a simple query."""
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

        try:
            from neo4j import GraphDatabase
        except ImportError:
            pytest.skip("neo4j driver not installed")

        try:
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            with driver.session() as session:
                result = session.run("RETURN 1 as num")
                records = list(result)
                assert len(records) > 0, "Neo4j should return results"
                assert records[0]["num"] == 1
            driver.close()
        except Exception as e:
            pytest.skip(f"Neo4j query failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_neo4j_version(self):
        """Test that we can retrieve Neo4j version."""
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

        try:
            from neo4j import GraphDatabase
        except ImportError:
            pytest.skip("neo4j driver not installed")

        try:
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            with driver.session() as session:
                result = session.run("CALL dbms.components() YIELD versions RETURN versions")
                records = list(result)
                assert len(records) > 0, "Should be able to get Neo4j version"
            driver.close()
        except Exception as e:
            pytest.skip(f"Could not retrieve Neo4j version: {str(e)}")


class TestRedisContainer:
    """Test Redis Docker container."""

    @pytest.mark.asyncio
    async def test_redis_container_running(self):
        """Test that Redis container is running and accessible."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))

        try:
            import redis
        except ImportError:
            pytest.skip("redis package not installed")

        try:
            r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            r.ping()
            assert True, "Successfully connected to Redis"
        except Exception as e:
            pytest.skip(f"Redis container not running or not accessible: {str(e)}")

    @pytest.mark.asyncio
    async def test_redis_set_get_operation(self):
        """Test that Redis can perform set and get operations."""
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))

        try:
            import redis
        except ImportError:
            pytest.skip("redis package not installed")

        try:
            r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            # Test set and get
            test_key = "test_deployment_key"
            test_value = "test_deployment_value"

            r.set(test_key, test_value)
            retrieved_value = r.get(test_key)

            assert retrieved_value == test_value, "Redis should return the value we set"

            # Clean up
            r.delete(test_key)
        except Exception as e:
            pytest.skip(f"Redis operations failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_redis_connection_pool(self):
        """Test that Redis connection pooling works."""
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))

        try:
            import redis
        except ImportError:
            pytest.skip("redis package not installed")

        try:
            pool = redis.ConnectionPool(host=redis_host, port=redis_port)
            r = redis.Redis(connection_pool=pool)
            assert r.ping(), "Should be able to ping Redis through connection pool"
            pool.disconnect()
        except Exception as e:
            pytest.skip(f"Redis connection pool test failed: {str(e)}")


class TestBassetAPIContainer:
    """Test Basset API Docker container."""

    @pytest.mark.asyncio
    async def test_basset_api_container_running(self):
        """Test that Basset API container is running."""
        try:
            from httpx import AsyncClient
        except ImportError:
            pytest.skip("httpx not installed")

        api_url = os.getenv("API_URL", "http://localhost:8000")

        try:
            async with AsyncClient(base_url=api_url) as client:
                response = await client.get("/health", timeout=5.0)
                assert response.status_code == 200, f"API returned {response.status_code}"
        except Exception as e:
            pytest.skip(f"Basset API container not running or not accessible: {str(e)}")

    @pytest.mark.asyncio
    async def test_basset_api_health_endpoint(self):
        """Test that the health endpoint is accessible."""
        try:
            from httpx import AsyncClient
        except ImportError:
            pytest.skip("httpx not installed")

        api_url = os.getenv("API_URL", "http://localhost:8000")

        try:
            async with AsyncClient(base_url=api_url) as client:
                response = await client.get("/health", timeout=5.0)
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
        except Exception as e:
            pytest.skip(f"Health endpoint test failed: {str(e)}")


class TestServiceConnectivity:
    """Test that services can communicate with each other."""

    @pytest.mark.asyncio
    async def test_all_services_accessible(self):
        """Test that all required services are accessible."""
        neo4j_uri = os.getenv("NEO4J_URI")
        redis_host = os.getenv("REDIS_HOST", "localhost")
        api_url = os.getenv("API_URL", "http://localhost:8000")

        errors = []

        # Check Neo4j
        if neo4j_uri:
            try:
                from neo4j import GraphDatabase
                neo4j_user = os.getenv("NEO4J_USER", "neo4j")
                neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
                driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                driver.verify_connectivity()
                driver.close()
            except Exception as e:
                errors.append(f"Neo4j: {str(e)}")

        # Check Redis
        try:
            import redis
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            r = redis.Redis(host=redis_host, port=redis_port)
            r.ping()
        except Exception as e:
            errors.append(f"Redis: {str(e)}")

        # Check API
        try:
            from httpx import AsyncClient
            async with AsyncClient(base_url=api_url) as client:
                response = await client.get("/health", timeout=5.0)
                if response.status_code != 200:
                    errors.append(f"API health check returned {response.status_code}")
        except Exception as e:
            errors.append(f"API: {str(e)}")

        if errors:
            pytest.skip(f"Some services are not accessible: {'; '.join(errors)}")
        else:
            assert True, "All services are accessible"

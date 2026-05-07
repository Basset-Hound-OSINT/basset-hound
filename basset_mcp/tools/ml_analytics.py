"""
MCP Tools for ML Analytics (Phase 8, Stream 5).

Provides Claude with tools to:
- Extract features from entities
- Detect duplicates
- Predict relationships
- Detect communities
- Detect anomalies

All tools work with Neo4j backend and require project_id.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger("basset_mcp.ml_analytics")


def register_tools(mcp):
    """Register ML Analytics tools with the MCP server."""

    @mcp.tool()
    async def extract_ml_features_for_project(project_id: str) -> dict:
        """
        Extract machine learning features from all entities in a project.

        Features extracted include:
        - Normalized entity names
        - Email domains
        - Normalized phone numbers
        - Entity types

        All features are normalized to 0-1 scale for ML model compatibility.

        Args:
            project_id: The ID of the project to process

        Returns:
            Dictionary with success status and number of features extracted
        """
        try:
            from api.services.ml_analytics_service import get_ml_analytics_service

            ml_service = await get_ml_analytics_service()
            result = await ml_service.extract_and_store_features(project_id)

            return {
                "success": result.get("success", False),
                "features_extracted": result.get("features_extracted", 0),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def detect_duplicate_entities(
        project_id: str, min_score: float = 0.7
    ) -> dict:
        """
        Detect potential duplicate entities using ML similarity scoring.

        Uses multiple similarity metrics:
        - Levenshtein distance for names
        - Email exact matching and domain matching
        - Phone exact matching
        - Entity type matching

        Returns duplicates scored 0-100 with reasoning.
        Target accuracy: >90%

        Args:
            project_id: The ID of the project to analyze
            min_score: Minimum similarity score (0.0-1.0) for flagging duplicates

        Returns:
            List of potential duplicate pairs with scores and reasoning
        """
        try:
            from api.services.ml_analytics_service import get_ml_analytics_service

            ml_service = await get_ml_analytics_service()
            result = await ml_service.detect_duplicates(project_id, min_score=min_score)

            return {
                "success": result.get("success", False),
                "count": result.get("count", 0),
                "duplicates": result.get("duplicates", []),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def predict_entity_relationships(
        project_id: str, entity_id: str, top_k: int = 5
    ) -> dict:
        """
        Predict likely relationships between an entity and other entities.

        Relationship types:
        - likely_duplicate: High confidence duplicate (>80% similarity)
        - likely_related: Probable connection (60-80% similarity)
        - possibly_related: Potential connection (40-60% similarity)

        Returns predictions scored 0-100 with confidence and reasoning.
        Target recall: >70%

        Args:
            project_id: The ID of the project
            entity_id: The ID of the entity to predict links for
            top_k: Number of predictions to return (1-50)

        Returns:
            List of predicted relationships with scores and reasoning
        """
        try:
            from api.services.ml_analytics_service import get_ml_analytics_service

            ml_service = await get_ml_analytics_service()
            result = await ml_service.predict_relationships(project_id, entity_id, top_k)

            return {
                "success": result.get("success", False),
                "count": result.get("count", 0),
                "predictions": result.get("predictions", []),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error(f"Link prediction failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def detect_entity_communities(project_id: str) -> dict:
        """
        Detect communities (clusters) in the entity graph using Louvain algorithm.

        Returns communities with:
        - Entity list
        - Community size
        - Modularity score (0.0-1.0)

        Modularity interpretation:
        - 0.8-1.0: Strong community structure
        - 0.6-0.8: Good community structure
        - 0.4-0.6: Moderate community structure
        - 0.0-0.4: Weak community structure

        Args:
            project_id: The ID of the project to analyze

        Returns:
            List of detected communities with modularity scores
        """
        try:
            from api.services.ml_analytics_service import get_ml_analytics_service

            ml_service = await get_ml_analytics_service()
            result = await ml_service.detect_communities(project_id)

            return {
                "success": result.get("success", False),
                "count": result.get("count", 0),
                "communities": result.get("communities", []),
                "avg_modularity": result.get("avg_modularity", 0.0),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def detect_entity_anomalies(project_id: str) -> dict:
        """
        Detect anomalies in entity data patterns.

        Detected anomalies:
        - rapid_updates: >50 updates per hour (severity: medium/high)
        - sparse_data: Missing >50% of required fields (severity: low)

        Returns alerts with:
        - Entity ID
        - Anomaly type
        - Severity level
        - Details dictionary

        Args:
            project_id: The ID of the project to analyze

        Returns:
            List of detected anomalies with severity and details
        """
        try:
            from api.services.ml_analytics_service import get_ml_analytics_service

            ml_service = await get_ml_analytics_service()
            result = await ml_service.detect_anomalies(project_id)

            return {
                "success": result.get("success", False),
                "count": result.get("count", 0),
                "alerts": result.get("alerts", []),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {"success": False, "error": str(e)}

    logger.info("ML Analytics tools registered successfully")

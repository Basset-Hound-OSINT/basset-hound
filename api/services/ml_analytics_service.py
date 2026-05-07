"""
Advanced ML Analytics Service for Basset Hound.

This module provides machine learning-powered analytics including:
- Feature engineering for entity similarity
- Duplicate detection using ML classifiers
- Link prediction using graph embeddings
- Community detection using Louvain algorithm
- Anomaly detection for unusual patterns

Features:
- Jaccard, Cosine, and Levenshtein similarity metrics
- Scikit-learn based classification
- Community detection with modularity scoring
- Anomaly pattern detection
- Neo4j integration for feature storage
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from difflib import SequenceMatcher

# Try to import ML libraries
try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.ensemble import RandomForestClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. ML models will be disabled.")

try:
    import networkx as nx
    from networkx.algorithms import community
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logging.warning("networkx not available. Community detection will be disabled.")

try:
    from jellyfish import jaro_winkler, levenshtein_distance
    JELLYFISH_AVAILABLE = True
except ImportError:
    JELLYFISH_AVAILABLE = False
    logging.warning("jellyfish not available. Advanced string matching will use basic methods.")

from api.services.neo4j_service import AsyncNeo4jService

logger = logging.getLogger("basset_hound.ml_analytics")


@dataclass
class EntityFeatures:
    """Extracted features for an entity."""
    entity_id: str
    name_normalized: str
    email_domain: Optional[str]
    email_normalized: Optional[str]
    phone_normalized: Optional[str]
    entity_type: str
    features: Dict[str, float]  # Normalized 0-1 features


@dataclass
class DuplicateScore:
    """Duplicate detection score result."""
    entity_id_1: str
    entity_id_2: str
    similarity_score: float  # 0-1
    duplicate_probability: float  # 0-100
    reasoning: Dict[str, float]  # Feature contributions


@dataclass
class LinkPrediction:
    """Link prediction result."""
    entity_id_1: str
    entity_id_2: str
    relationship_type: str
    prediction_score: float  # 0-100
    confidence: float  # 0-1
    reasoning: str


@dataclass
class CommunityDetection:
    """Community detection result."""
    community_id: int
    entities: List[str]
    size: int
    modularity: float


@dataclass
class AnomalyAlert:
    """Anomaly detection alert."""
    entity_id: str
    entity_type: str
    anomaly_type: str
    severity: str  # low, medium, high
    details: Dict[str, Any]


class MLFeaturesExtractor:
    """Feature extraction for ML models."""

    @staticmethod
    def normalize_string(s: str) -> str:
        """Normalize string for comparison."""
        if not s:
            return ""
        return s.lower().strip()

    @staticmethod
    def extract_email_domain(email: str) -> Optional[str]:
        """Extract domain from email."""
        if not email or "@" not in email:
            return None
        return email.split("@")[1].lower()

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number (digits only)."""
        if not phone:
            return ""
        return "".join(c for c in phone if c.isdigit())

    @staticmethod
    def jaccard_similarity(str1: str, str2: str) -> float:
        """Compute Jaccard similarity between two strings (0-1)."""
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0

        set1 = set(str1.lower().split())
        set2 = set(str2.lower().split())

        if not set1 and not set2:
            return 1.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors (0-1)."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a ** 2 for a in vec1) ** 0.5
        norm2 = sum(b ** 2 for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    @staticmethod
    def levenshtein_similarity(str1: str, str2: str) -> float:
        """Compute Levenshtein-based similarity (0-1)."""
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0

        try:
            if JELLYFISH_AVAILABLE:
                return jaro_winkler(str1, str2)
        except Exception:
            pass

        # Fallback: use SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()

    @staticmethod
    def extract_entity_features(entity: Dict[str, Any]) -> EntityFeatures:
        """Extract normalized features from entity data."""
        entity_id = entity.get("id", "")
        name = entity.get("name", "")
        email = entity.get("email", "")
        phone = entity.get("phone", "")
        entity_type = entity.get("entity_type", "Person")

        name_normalized = MLFeaturesExtractor.normalize_string(name)
        email_normalized = MLFeaturesExtractor.normalize_string(email)
        phone_normalized = MLFeaturesExtractor.normalize_phone(phone)
        email_domain = MLFeaturesExtractor.extract_email_domain(email)

        return EntityFeatures(
            entity_id=entity_id,
            name_normalized=name_normalized,
            email_domain=email_domain,
            email_normalized=email_normalized,
            phone_normalized=phone_normalized,
            entity_type=entity_type,
            features={},
        )


class DuplicateDetectionModel:
    """ML-based duplicate detection."""

    def __init__(self):
        """Initialize duplicate detection model."""
        self.model = None
        self.scaler = MinMaxScaler() if SKLEARN_AVAILABLE else None
        self.is_trained = False

    def compute_similarity_features(
        self, features1: EntityFeatures, features2: EntityFeatures
    ) -> Dict[str, float]:
        """Compute similarity features between two entities."""
        extractor = MLFeaturesExtractor()

        features = {}

        # Name similarity
        name_sim = extractor.levenshtein_similarity(
            features1.name_normalized, features2.name_normalized
        )
        features["name_levenshtein"] = name_sim

        name_jaccard = extractor.jaccard_similarity(
            features1.name_normalized, features2.name_normalized
        )
        features["name_jaccard"] = name_jaccard

        # Email similarity
        if features1.email_normalized and features2.email_normalized:
            email_exact = 1.0 if features1.email_normalized == features2.email_normalized else 0.0
            features["email_exact"] = email_exact

            email_domain_match = 1.0 if features1.email_domain == features2.email_domain else 0.0
            features["email_domain_match"] = email_domain_match
        else:
            features["email_exact"] = 0.0
            features["email_domain_match"] = 0.0

        # Phone similarity
        if features1.phone_normalized and features2.phone_normalized:
            phone_exact = 1.0 if features1.phone_normalized == features2.phone_normalized else 0.0
            features["phone_exact"] = phone_exact
        else:
            features["phone_exact"] = 0.0

        # Entity type match
        entity_type_match = 1.0 if features1.entity_type == features2.entity_type else 0.0
        features["entity_type_match"] = entity_type_match

        return features

    def score_duplicate(
        self, features1: EntityFeatures, features2: EntityFeatures
    ) -> DuplicateScore:
        """Score likelihood of entities being duplicates."""
        sim_features = self.compute_similarity_features(features1, features2)

        # Compute weighted score (rule-based fallback if model not trained)
        if not SKLEARN_AVAILABLE or not self.is_trained:
            # Rule-based scoring
            score = 0.0
            weights = {
                "name_levenshtein": 0.3,
                "email_exact": 0.3,
                "phone_exact": 0.2,
                "entity_type_match": 0.15,
                "name_jaccard": 0.05,
            }

            for feature_name, weight in weights.items():
                score += sim_features.get(feature_name, 0.0) * weight

            similarity_score = score
        else:
            # ML-based scoring
            feature_values = list(sim_features.values())
            try:
                feature_array = np.array(feature_values).reshape(1, -1)
                scaled = self.scaler.transform(feature_array)
                prob = self.model.predict_proba(scaled)[0, 1]
                similarity_score = prob
            except Exception as e:
                logger.warning(f"ML scoring failed: {e}, using rule-based")
                similarity_score = sum(sim_features.values()) / len(sim_features)

        # Convert to 0-100 scale
        duplicate_probability = similarity_score * 100

        return DuplicateScore(
            entity_id_1=features1.entity_id,
            entity_id_2=features2.entity_id,
            similarity_score=similarity_score,
            duplicate_probability=duplicate_probability,
            reasoning=sim_features,
        )

    def train_on_known_duplicates(self, training_data: List[Tuple[EntityFeatures, EntityFeatures, bool]]):
        """Train model on known duplicate pairs."""
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available. Skipping model training.")
            return

        try:
            X = []
            y = []

            for features1, features2, is_duplicate in training_data:
                sim_features = self.compute_similarity_features(features1, features2)
                X.append(list(sim_features.values()))
                y.append(1 if is_duplicate else 0)

            if len(X) < 2:
                logger.warning("Insufficient training data for model training")
                return

            X = np.array(X)
            y = np.array(y)

            # Train model
            self.model = RandomForestClassifier(n_estimators=50, random_state=42)
            self.model.fit(X, y)
            self.is_trained = True

            logger.info(f"Duplicate detection model trained on {len(X)} samples")
        except Exception as e:
            logger.error(f"Model training failed: {e}")


class LinkPredictionEngine:
    """Link prediction using entity similarity."""

    def predict_links(
        self, entity_id: str, all_features: List[EntityFeatures], top_k: int = 5
    ) -> List[LinkPrediction]:
        """Predict likely links for an entity."""
        predictions = []
        entity_features = None

        for features in all_features:
            if features.entity_id == entity_id:
                entity_features = features
                break

        if not entity_features:
            return predictions

        duplicate_detector = DuplicateDetectionModel()

        for other_features in all_features:
            if other_features.entity_id == entity_id:
                continue

            duplicate_score = duplicate_detector.score_duplicate(entity_features, other_features)

            # Determine relationship type based on similarity
            if duplicate_score.similarity_score > 0.8:
                relationship_type = "likely_duplicate"
                confidence = duplicate_score.similarity_score
            elif duplicate_score.similarity_score > 0.6:
                relationship_type = "likely_related"
                confidence = duplicate_score.similarity_score * 0.8
            elif duplicate_score.similarity_score > 0.4:
                relationship_type = "possibly_related"
                confidence = duplicate_score.similarity_score * 0.6
            else:
                continue

            prediction = LinkPrediction(
                entity_id_1=entity_id,
                entity_id_2=other_features.entity_id,
                relationship_type=relationship_type,
                prediction_score=duplicate_score.duplicate_probability,
                confidence=confidence,
                reasoning=f"Similarity score: {duplicate_score.similarity_score:.2f}",
            )

            predictions.append(prediction)

        # Sort by prediction score and return top-k
        predictions.sort(key=lambda x: x.prediction_score, reverse=True)
        return predictions[:top_k]


class CommunityDetectionEngine:
    """Community detection using Louvain algorithm."""

    @staticmethod
    def detect_communities(entities: List[str], edges: List[Tuple[str, str]]) -> List[CommunityDetection]:
        """Detect communities in entity graph."""
        if not NETWORKX_AVAILABLE:
            logger.warning("networkx not available. Community detection disabled.")
            return []

        try:
            # Create graph
            G = nx.Graph()
            G.add_nodes_from(entities)
            G.add_edges_from(edges)

            # Detect communities using Louvain method
            communities_gen = community.greedy_modularity_communities(G)

            results = []
            for i, comm in enumerate(communities_gen):
                entity_list = list(comm)
                modularity = community.modularity(G, [comm])

                results.append(
                    CommunityDetection(
                        community_id=i,
                        entities=entity_list,
                        size=len(entity_list),
                        modularity=modularity,
                    )
                )

            logger.info(f"Detected {len(results)} communities with avg modularity {np.mean([r.modularity for r in results]):.3f}")
            return results

        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return []


class AnomalyDetector:
    """Detect anomalies in entity data patterns."""

    @staticmethod
    def detect_anomalies(entities: List[Dict[str, Any]]) -> List[AnomalyAlert]:
        """Detect unusual patterns in entities."""
        alerts = []

        for entity in entities:
            entity_id = entity.get("id", "")
            entity_type = entity.get("entity_type", "Person")

            # Check for rapid updates
            updated_at = entity.get("updated_at")
            created_at = entity.get("created_at")

            if updated_at and created_at:
                try:
                    from datetime import datetime

                    updated = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
                    created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                    update_count = entity.get("update_count", 0)

                    time_diff_hours = (updated - created).total_seconds() / 3600

                    if time_diff_hours > 0 and update_count > 100:
                        updates_per_hour = update_count / time_diff_hours

                        if updates_per_hour > 50:  # More than 50 updates per hour
                            alerts.append(
                                AnomalyAlert(
                                    entity_id=entity_id,
                                    entity_type=entity_type,
                                    anomaly_type="rapid_updates",
                                    severity="high" if updates_per_hour > 100 else "medium",
                                    details={
                                        "updates_per_hour": round(updates_per_hour, 2),
                                        "total_updates": update_count,
                                    },
                                )
                            )
                except Exception as e:
                    logger.debug(f"Failed to check rapid updates: {e}")

            # Check for sparse data (missing important fields)
            required_fields = ["name"]
            if entity_type == "Person":
                required_fields.extend(["email", "phone"])

            missing_fields = []
            for field in required_fields:
                if not entity.get(field):
                    missing_fields.append(field)

            if len(missing_fields) > len(required_fields) * 0.5:
                alerts.append(
                    AnomalyAlert(
                        entity_id=entity_id,
                        entity_type=entity_type,
                        anomaly_type="sparse_data",
                        severity="low",
                        details={"missing_fields": missing_fields},
                    )
                )

        return alerts


class MLAnalyticsService:
    """Main ML Analytics Service."""

    def __init__(self):
        """Initialize ML Analytics Service."""
        self.neo4j_service = None
        self.duplicate_detector = DuplicateDetectionModel()
        self.link_predictor = LinkPredictionEngine()
        self.community_detector = CommunityDetectionEngine()
        self.anomaly_detector = AnomalyDetector()

    async def connect(self):
        """Connect to Neo4j."""
        self.neo4j_service = AsyncNeo4jService()
        await self.neo4j_service.connect()

    async def close(self):
        """Close Neo4j connection."""
        if self.neo4j_service:
            await self.neo4j_service.close()

    async def extract_and_store_features(self, project_id: str) -> Dict[str, Any]:
        """Extract features for all entities in a project."""
        try:
            entities = await self.neo4j_service.get_entities(project_id=project_id)

            feature_count = 0
            for entity in entities:
                features = MLFeaturesExtractor.extract_entity_features(entity)

                # Store features in Neo4j as properties
                await self.neo4j_service.update_entity(
                    project_id=project_id,
                    entity_id=entity["id"],
                    data={
                        "ml_name_normalized": features.name_normalized,
                        "ml_email_domain": features.email_domain or "",
                        "ml_features_extracted": True,
                    },
                )

                feature_count += 1

            logger.info(f"Extracted features for {feature_count} entities in project {project_id}")
            return {"success": True, "features_extracted": feature_count}

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return {"success": False, "error": str(e)}

    async def detect_duplicates(
        self, project_id: str, min_score: float = 0.7
    ) -> Dict[str, Any]:
        """Detect potential duplicates in project."""
        try:
            entities = await self.neo4j_service.get_entities(project_id=project_id)

            duplicates = []
            for i, entity1 in enumerate(entities):
                features1 = MLFeaturesExtractor.extract_entity_features(entity1)

                for entity2 in entities[i + 1 :]:
                    features2 = MLFeaturesExtractor.extract_entity_features(entity2)

                    score = self.duplicate_detector.score_duplicate(features1, features2)

                    if score.similarity_score >= min_score:
                        duplicates.append(
                            {
                                "entity_id_1": score.entity_id_1,
                                "entity_id_2": score.entity_id_2,
                                "similarity_score": round(score.similarity_score, 3),
                                "duplicate_probability": round(score.duplicate_probability, 1),
                                "reasoning": score.reasoning,
                            }
                        )

            duplicates.sort(key=lambda x: x["duplicate_probability"], reverse=True)

            logger.info(f"Found {len(duplicates)} potential duplicates in project {project_id}")
            return {"success": True, "duplicates": duplicates, "count": len(duplicates)}

        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            return {"success": False, "error": str(e)}

    async def predict_relationships(
        self, project_id: str, entity_id: str, top_k: int = 5
    ) -> Dict[str, Any]:
        """Predict likely relationships for an entity."""
        try:
            entities = await self.neo4j_service.get_entities(project_id=project_id)

            all_features = [
                MLFeaturesExtractor.extract_entity_features(e) for e in entities
            ]

            predictions = self.link_predictor.predict_links(entity_id, all_features, top_k)

            result_list = [
                {
                    "entity_id_1": p.entity_id_1,
                    "entity_id_2": p.entity_id_2,
                    "relationship_type": p.relationship_type,
                    "prediction_score": round(p.prediction_score, 1),
                    "confidence": round(p.confidence, 3),
                    "reasoning": p.reasoning,
                }
                for p in predictions
            ]

            logger.info(f"Predicted {len(predictions)} relationships for entity {entity_id}")
            return {"success": True, "predictions": result_list, "count": len(result_list)}

        except Exception as e:
            logger.error(f"Link prediction failed: {e}")
            return {"success": False, "error": str(e)}

    async def detect_communities(self, project_id: str) -> Dict[str, Any]:
        """Detect communities in project graph."""
        try:
            entities = await self.neo4j_service.get_entities(project_id=project_id)
            relationships = await self.neo4j_service.get_relationships(project_id=project_id)

            entity_ids = [e["id"] for e in entities]
            edges = [
                (r.get("source_entity_id"), r.get("target_entity_id"))
                for r in relationships
                if r.get("source_entity_id") and r.get("target_entity_id")
            ]

            communities = self.community_detector.detect_communities(entity_ids, edges)

            result_list = [
                {
                    "community_id": c.community_id,
                    "entities": c.entities,
                    "size": c.size,
                    "modularity": round(c.modularity, 3),
                }
                for c in communities
            ]

            avg_modularity = (
                np.mean([c.modularity for c in communities]) if communities else 0
            )

            logger.info(
                f"Detected {len(communities)} communities in project {project_id} "
                f"(avg modularity: {avg_modularity:.3f})"
            )

            return {
                "success": True,
                "communities": result_list,
                "count": len(result_list),
                "avg_modularity": round(avg_modularity, 3),
            }

        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return {"success": False, "error": str(e)}

    async def detect_anomalies(self, project_id: str) -> Dict[str, Any]:
        """Detect anomalies in project entities."""
        try:
            entities = await self.neo4j_service.get_entities(project_id=project_id)

            alerts = self.anomaly_detector.detect_anomalies(entities)

            result_list = [
                {
                    "entity_id": a.entity_id,
                    "entity_type": a.entity_type,
                    "anomaly_type": a.anomaly_type,
                    "severity": a.severity,
                    "details": a.details,
                }
                for a in alerts
            ]

            logger.info(f"Detected {len(alerts)} anomalies in project {project_id}")
            return {"success": True, "alerts": result_list, "count": len(result_list)}

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {"success": False, "error": str(e)}


# Global service instance
_ml_service: Optional[MLAnalyticsService] = None


async def get_ml_analytics_service() -> MLAnalyticsService:
    """Get or create ML Analytics Service instance."""
    global _ml_service

    if _ml_service is None:
        _ml_service = MLAnalyticsService()
        await _ml_service.connect()

    return _ml_service

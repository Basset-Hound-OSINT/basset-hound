"""
Matching Engine for Smart Suggestions in Basset Hound OSINT Platform.

This module provides intelligent matching capabilities for finding potential matches
between DataItems based on exact hash, exact string, and partial matching. It's designed
to help human operators identify relationships between entities and orphaned data.

Features:
- Exact hash matching (1.0 confidence)
- Exact string matching for normalized identifiers (0.95 confidence)
- Partial matching with configurable thresholds (0.5-0.9 confidence)
- Token-based matching for complex strings like addresses
- Unicode and special character handling

Phase 43.3: Smart Suggestions & Data Matching System
"""

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from api.services.fuzzy_matcher import FuzzyMatcher, MatchStrategy
from api.services.normalizer import DataNormalizer, get_normalizer
from api.services.neo4j_service import AsyncNeo4jService

logger = logging.getLogger("basset_hound.matching_engine")


# Try to import phonenumbers for E.164 formatting
try:
    import phonenumbers
    PHONENUMBERS_AVAILABLE = True
except ImportError:
    PHONENUMBERS_AVAILABLE = False
    logger.warning("phonenumbers library not available. Phone normalization will be basic.")


@dataclass
class MatchResult:
    """
    Represents a potential match between data items.

    Attributes:
        entity_id: ID of the entity containing the matching data
        data_id: ID of the specific data item that matched
        field_type: Type of field (e.g., 'email', 'phone', 'name')
        field_value: The actual value that matched
        confidence: Match confidence score (0.0-1.0)
        match_type: Type of match ('exact_hash', 'exact_string', 'partial_string')
        similarity_score: For partial matches, the similarity score
    """
    entity_id: str
    data_id: Optional[str]
    field_type: str
    field_value: str
    confidence: float
    match_type: str
    similarity_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "entity_id": self.entity_id,
            "data_id": self.data_id,
            "field_type": self.field_type,
            "field_value": self.field_value,
            "confidence": self.confidence,
            "match_type": self.match_type,
            "similarity_score": self.similarity_score
        }


class StringNormalizer:
    """
    Advanced string normalization for matching purposes.

    Provides specialized normalization beyond basic DataNormalizer
    for fuzzy matching and comparison.
    """

    @staticmethod
    def normalize_email(email: str) -> str:
        """
        Normalize email for matching.

        - Lowercase
        - Strip whitespace
        - Handle plus-addressing (keep both forms)

        Args:
            email: Email address to normalize

        Returns:
            Normalized email string
        """
        if not email:
            return ""

        email = email.strip().lower()
        return email

    @staticmethod
    def normalize_phone_e164(phone: str, default_region: str = "US") -> str:
        """
        Normalize phone to E.164 format if possible.

        Args:
            phone: Phone number to normalize
            default_region: Default country code for parsing

        Returns:
            E.164 formatted phone or cleaned digits
        """
        if not phone:
            return ""

        if PHONENUMBERS_AVAILABLE:
            try:
                # Parse the phone number
                parsed = phonenumbers.parse(phone, default_region)

                # Format to E.164
                if phonenumbers.is_valid_number(parsed):
                    return phonenumbers.format_number(
                        parsed,
                        phonenumbers.PhoneNumberFormat.E164
                    )
            except Exception as e:
                logger.debug(f"Phone parsing failed: {e}")

        # Fallback: just strip non-digits
        digits = re.sub(r'\D', '', phone)
        return f"+{digits}" if digits else ""

    @staticmethod
    def normalize_address(address: str) -> str:
        """
        Normalize address for matching.

        - Lowercase
        - Remove punctuation
        - Strip whitespace
        - Normalize common abbreviations

        Args:
            address: Address to normalize

        Returns:
            Normalized address string
        """
        if not address:
            return ""

        # Lowercase
        result = address.lower()

        # Remove diacritics
        result = unicodedata.normalize('NFD', result)
        result = ''.join(
            char for char in result
            if unicodedata.category(char) != 'Mn'
        )

        # Common abbreviations
        abbreviations = {
            r'\bstreet\b': 'st',
            r'\bavenue\b': 'ave',
            r'\bboulevard\b': 'blvd',
            r'\broad\b': 'rd',
            r'\bdrive\b': 'dr',
            r'\bcourt\b': 'ct',
            r'\blane\b': 'ln',
            r'\bapartment\b': 'apt',
            r'\bsuite\b': 'ste',
            r'\bnorth\b': 'n',
            r'\bsouth\b': 's',
            r'\beast\b': 'e',
            r'\bwest\b': 'w',
        }

        for pattern, replacement in abbreviations.items():
            result = re.sub(pattern, replacement, result)

        # Remove punctuation except spaces and hyphens
        result = re.sub(r'[^\w\s-]', '', result)

        # Collapse whitespace
        result = re.sub(r'\s+', ' ', result)

        return result.strip()

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize name for matching.

        - Lowercase
        - Remove middle initials
        - Remove diacritics
        - Strip whitespace

        Args:
            name: Name to normalize

        Returns:
            Normalized name string
        """
        if not name:
            return ""

        # Lowercase
        result = name.lower()

        # Remove diacritics
        result = unicodedata.normalize('NFD', result)
        result = ''.join(
            char for char in result
            if unicodedata.category(char) != 'Mn'
        )

        # Remove single letter middle initials (with or without period)
        result = re.sub(r'\s+[a-z]\.\s+', ' ', result)
        result = re.sub(r'\s+[a-z]\s+', ' ', result)

        # Remove special characters except spaces and hyphens
        result = re.sub(r'[^\w\s-]', '', result)

        # Collapse whitespace
        result = re.sub(r'\s+', ' ', result)

        return result.strip()

    @staticmethod
    def calculate_hash(value: str) -> str:
        """
        Calculate SHA-256 hash of a value.

        Args:
            value: Value to hash

        Returns:
            Hex digest of SHA-256 hash
        """
        if not value:
            return ""

        return hashlib.sha256(value.encode('utf-8')).hexdigest()


class MatchingEngine:
    """
    Matching engine for finding potential data matches in the database.

    This engine provides three levels of matching:
    1. Exact hash matches (1.0 confidence)
    2. Exact string matches after normalization (0.95 confidence)
    3. Partial matches using fuzzy string matching (0.5-0.9 confidence)

    Usage:
        async with MatchingEngine() as engine:
            # Find all matches for a data item
            matches = await engine.find_all_matches(data_item)

            # Find specific match types
            hash_matches = await engine.find_exact_hash_matches(hash_value)
            exact_matches = await engine.find_exact_string_matches(value, field_type)
            partial_matches = await engine.find_partial_matches(value, field_type)
    """

    def __init__(self, neo4j_service: Optional[AsyncNeo4jService] = None):
        """
        Initialize the matching engine.

        Args:
            neo4j_service: Optional Neo4j service instance. If not provided,
                          a new instance will be created.
        """
        self.neo4j_service = neo4j_service or AsyncNeo4jService()
        self._owns_neo4j = neo4j_service is None
        self.normalizer = get_normalizer()
        self.fuzzy_matcher = FuzzyMatcher()
        self.string_normalizer = StringNormalizer()

    async def __aenter__(self):
        """Async context manager entry."""
        if self._owns_neo4j:
            await self.neo4j_service.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._owns_neo4j:
            await self.neo4j_service.close()

    async def find_exact_hash_matches(self, hash_value: str) -> List[MatchResult]:
        """
        Find all data items with exact hash match.

        This is the highest confidence match (1.0) and is used for
        files, images, and other binary data.

        Args:
            hash_value: SHA-256 hash to search for

        Returns:
            List of MatchResult objects with confidence 1.0
        """
        if not hash_value:
            return []

        try:
            # Query Neo4j for data items with matching hash
            # Assuming data items are stored as properties on Entity nodes
            # or as separate DataItem nodes
            query = """
            MATCH (e:Entity)
            UNWIND keys(e.profile) as section
            UNWIND keys(e.profile[section]) as field
            WITH e, section, field, e.profile[section][field] as values
            UNWIND values as value
            WHERE value.hash = $hash OR value.file_hash = $hash
            RETURN e.id as entity_id,
                   section + '.' + field as field_type,
                   value as field_value,
                   coalesce(value.id, null) as data_id
            LIMIT 100
            """

            async with self.neo4j_service._driver.session() as session:
                result = await session.run(query, {"hash": hash_value})
                records = await result.data()

            matches = []
            for record in records:
                matches.append(MatchResult(
                    entity_id=record["entity_id"],
                    data_id=record.get("data_id"),
                    field_type=record["field_type"],
                    field_value=str(record["field_value"]),
                    confidence=1.0,
                    match_type="exact_hash",
                    similarity_score=1.0
                ))

            return matches

        except Exception as e:
            logger.error(f"Error finding hash matches: {e}")
            return []

    async def find_exact_string_matches(
        self,
        normalized_value: str,
        field_type: str
    ) -> List[MatchResult]:
        """
        Find exact string matches after normalization.

        Used for identifiers like email, phone, crypto addresses where
        exact matching (after normalization) is reliable.

        Args:
            normalized_value: Normalized value to search for
            field_type: Type of field (email, phone, crypto_address, etc.)

        Returns:
            List of MatchResult objects with confidence 0.95
        """
        if not normalized_value or not field_type:
            return []

        try:
            # Query both entities and orphan data
            query = """
            // Search in Entity profiles
            MATCH (e:Entity)
            UNWIND keys(e.profile) as section
            UNWIND keys(e.profile[section]) as field
            WITH e, section, field, e.profile[section][field] as values
            WHERE field = $field_type OR section + '.' + field = $field_type
            UNWIND values as value
            WITH e, section, field, value,
                 CASE
                   WHEN value.normalized_value = $normalized_value THEN true
                   WHEN toLower(toString(value)) = $normalized_value THEN true
                   ELSE false
                 END as is_match
            WHERE is_match
            RETURN e.id as entity_id,
                   section + '.' + field as field_type,
                   value as field_value,
                   coalesce(value.id, null) as data_id,
                   'entity' as source

            UNION

            // Search in Orphan Data
            MATCH (o:OrphanData)
            WHERE (o.identifier_type = $field_type OR o.type = $field_type)
              AND (o.normalized_value = $normalized_value
                   OR toLower(o.identifier_value) = $normalized_value)
            RETURN o.id as entity_id,
                   o.identifier_type as field_type,
                   o.identifier_value as field_value,
                   o.id as data_id,
                   'orphan' as source

            LIMIT 100
            """

            async with self.neo4j_service._driver.session() as session:
                result = await session.run(
                    query,
                    {
                        "normalized_value": normalized_value.lower(),
                        "field_type": field_type
                    }
                )
                records = await result.data()

            matches = []
            for record in records:
                matches.append(MatchResult(
                    entity_id=record["entity_id"],
                    data_id=record.get("data_id"),
                    field_type=record["field_type"],
                    field_value=str(record["field_value"]),
                    confidence=0.95,
                    match_type="exact_string",
                    similarity_score=1.0
                ))

            return matches

        except Exception as e:
            logger.error(f"Error finding exact string matches: {e}")
            return []

    async def find_partial_matches(
        self,
        normalized_value: str,
        field_type: str,
        threshold: float = 0.7
    ) -> List[Tuple[MatchResult, float]]:
        """
        Find partial matches using fuzzy string matching.

        Used for names, addresses, and other text where partial matches
        are meaningful. Uses Levenshtein distance and token-based matching.

        Args:
            normalized_value: Normalized value to search for
            field_type: Type of field (name, address, etc.)
            threshold: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of tuples (MatchResult, similarity_score)
        """
        if not normalized_value or not field_type:
            return []

        if threshold < 0.5 or threshold > 1.0:
            threshold = 0.7

        try:
            # Get all candidate values from database
            query = """
            // Search in Entity profiles
            MATCH (e:Entity)
            UNWIND keys(e.profile) as section
            UNWIND keys(e.profile[section]) as field
            WITH e, section, field, e.profile[section][field] as values
            WHERE field = $field_type OR section + '.' + field = $field_type
            UNWIND values as value
            RETURN e.id as entity_id,
                   section + '.' + field as field_type,
                   value as field_value,
                   coalesce(value.id, null) as data_id,
                   'entity' as source

            UNION

            // Search in Orphan Data
            MATCH (o:OrphanData)
            WHERE o.identifier_type = $field_type OR o.type = $field_type
            RETURN o.id as entity_id,
                   o.identifier_type as field_type,
                   o.identifier_value as field_value,
                   o.id as data_id,
                   'orphan' as source

            LIMIT 1000
            """

            async with self.neo4j_service._driver.session() as session:
                result = await session.run(query, {"field_type": field_type})
                records = await result.data()

            # Perform fuzzy matching
            matches = []

            # Choose matching strategy based on field type
            if field_type in ['name', 'first_name', 'last_name', 'full_name']:
                strategy = MatchStrategy.JARO_WINKLER
                normalize_func = self.string_normalizer.normalize_name
            elif field_type in ['address', 'street_address', 'location']:
                strategy = MatchStrategy.TOKEN_SET_RATIO
                normalize_func = self.string_normalizer.normalize_address
            else:
                strategy = MatchStrategy.LEVENSHTEIN
                normalize_func = lambda x: str(x).lower().strip()

            normalized_search = normalize_func(normalized_value)

            for record in records:
                field_val = str(record["field_value"])
                if isinstance(record["field_value"], dict):
                    # Extract relevant field from structured data
                    if 'value' in record["field_value"]:
                        field_val = str(record["field_value"]['value'])
                    else:
                        field_val = str(record["field_value"])

                normalized_candidate = normalize_func(field_val)

                if not normalized_candidate:
                    continue

                # Calculate similarity
                similarity = self.fuzzy_matcher.calculate_similarity(
                    normalized_search,
                    normalized_candidate,
                    strategy=strategy,
                    normalize=False  # Already normalized
                )

                if similarity >= threshold:
                    # Calculate confidence based on similarity
                    confidence = self._calculate_confidence(similarity)

                    match = MatchResult(
                        entity_id=record["entity_id"],
                        data_id=record.get("data_id"),
                        field_type=record["field_type"],
                        field_value=field_val,
                        confidence=confidence,
                        match_type="partial_string",
                        similarity_score=similarity
                    )

                    matches.append((match, similarity))

            # Sort by similarity descending
            matches.sort(key=lambda x: x[1], reverse=True)

            return matches

        except Exception as e:
            logger.error(f"Error finding partial matches: {e}")
            return []

    def _calculate_confidence(self, similarity: float) -> float:
        """
        Calculate confidence score based on similarity.

        Confidence scoring:
        - >0.90: 0.9 confidence
        - 0.80-0.90: 0.7-0.9 confidence (linear)
        - 0.70-0.80: 0.5-0.7 confidence (linear)
        - <0.70: Don't suggest (handled by threshold)

        Args:
            similarity: Similarity score (0.0-1.0)

        Returns:
            Confidence score (0.5-1.0)
        """
        if similarity >= 0.90:
            return 0.9
        elif similarity >= 0.80:
            # Linear interpolation between 0.7 and 0.9
            return 0.7 + (similarity - 0.80) * 2.0
        elif similarity >= 0.70:
            # Linear interpolation between 0.5 and 0.7
            return 0.5 + (similarity - 0.70) * 2.0
        else:
            return 0.5

    async def find_all_matches(
        self,
        value: str,
        field_type: str,
        include_partial: bool = True,
        partial_threshold: float = 0.7
    ) -> List[Tuple[MatchResult, float, str]]:
        """
        Find all possible matches for a data value.

        This is the main entry point for finding matches. It tries:
        1. Exact hash matching (if applicable)
        2. Exact string matching after normalization
        3. Partial/fuzzy matching (optional)

        Args:
            value: Value to search for
            field_type: Type of field
            include_partial: Whether to include partial matches
            partial_threshold: Minimum similarity for partial matches

        Returns:
            List of tuples (MatchResult, confidence, match_type)
            Sorted by confidence descending
        """
        all_matches = []

        # Try hash matching for file/binary types
        if field_type in ['file', 'image', 'document', 'binary']:
            # Check if value is already a hash
            if len(value) == 64 and re.match(r'^[a-f0-9]{64}$', value.lower()):
                hash_matches = await self.find_exact_hash_matches(value)
                for match in hash_matches:
                    all_matches.append((match, match.confidence, match.match_type))
            else:
                # Calculate hash of value
                hash_value = self.string_normalizer.calculate_hash(value)
                hash_matches = await self.find_exact_hash_matches(hash_value)
                for match in hash_matches:
                    all_matches.append((match, match.confidence, match.match_type))

        # Normalize value based on type
        if field_type == 'email':
            normalized = self.string_normalizer.normalize_email(value)
        elif field_type == 'phone':
            normalized = self.string_normalizer.normalize_phone_e164(value)
        elif field_type in ['address', 'street_address', 'location']:
            normalized = self.string_normalizer.normalize_address(value)
        elif field_type in ['name', 'first_name', 'last_name', 'full_name']:
            normalized = self.string_normalizer.normalize_name(value)
        else:
            # Use DataNormalizer for other types
            norm_result = self.normalizer.normalize(value, field_type)
            normalized = norm_result.normalized

        # Try exact string matching
        if normalized:
            exact_matches = await self.find_exact_string_matches(normalized, field_type)
            for match in exact_matches:
                all_matches.append((match, match.confidence, match.match_type))

        # Try partial matching if requested
        if include_partial and normalized:
            partial_matches = await self.find_partial_matches(
                normalized,
                field_type,
                partial_threshold
            )
            for match, similarity in partial_matches:
                all_matches.append((match, match.confidence, match.match_type))

        # Sort by confidence descending
        all_matches.sort(key=lambda x: x[1], reverse=True)

        return all_matches


# Module-level singleton
_matching_engine_instance: Optional[MatchingEngine] = None


async def get_matching_engine() -> MatchingEngine:
    """
    Get or create the singleton MatchingEngine instance.

    Returns:
        MatchingEngine instance
    """
    global _matching_engine_instance

    if _matching_engine_instance is None:
        _matching_engine_instance = MatchingEngine()
        await _matching_engine_instance.__aenter__()

    return _matching_engine_instance

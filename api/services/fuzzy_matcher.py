"""
Fuzzy Matching Service for Basset Hound OSINT Platform.

This module provides fuzzy string matching capabilities for auto-linking entities
based on similar (but not identical) field values. It complements the exact-match
auto-linker with fuzzy and phonetic matching algorithms.

Phase 5+ Feature: Entity Auto-Linking with Fuzzy Matching
"""

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from rapidfuzz import fuzz
    from rapidfuzz.distance import Levenshtein, JaroWinkler
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class MatchType(str, Enum):
    """Types of string matching."""
    EXACT = "exact"
    FUZZY = "fuzzy"
    PHONETIC = "phonetic"


class MatchStrategy(str, Enum):
    """Fuzzy matching strategies."""
    LEVENSHTEIN = "levenshtein"
    JARO_WINKLER = "jaro_winkler"
    TOKEN_SET_RATIO = "token_set_ratio"
    TOKEN_SORT_RATIO = "token_sort_ratio"
    PARTIAL_RATIO = "partial_ratio"


@dataclass
class FuzzyMatch:
    """
    Represents a fuzzy match between two entities.

    Attributes:
        entity1_id: ID of the first entity
        entity2_id: ID of the second entity
        field_path: Path to the matched field (e.g., 'core.name.first_name')
        value1: The value from entity1
        value2: The value from entity2
        similarity: Similarity score between 0.0 and 1.0
        match_type: Type of match (exact, fuzzy, or phonetic)
    """
    entity1_id: str
    entity2_id: str
    field_path: str
    value1: str
    value2: str
    similarity: float
    match_type: str = MatchType.FUZZY.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "entity1_id": self.entity1_id,
            "entity2_id": self.entity2_id,
            "field_path": self.field_path,
            "value1": self.value1,
            "value2": self.value2,
            "similarity": self.similarity,
            "match_type": self.match_type
        }


def double_metaphone(s: str) -> Tuple[str, str]:
    """
    Generate Double Metaphone codes for a string.

    This is a simplified implementation of Double Metaphone that handles
    common English name patterns. It returns two codes: primary and alternate.

    Args:
        s: Input string to encode

    Returns:
        Tuple of (primary_code, alternate_code)
    """
    if not s:
        return ("", "")

    # Normalize input
    s = s.upper().strip()

    # Remove non-alphabetic characters
    s = re.sub(r'[^A-Z]', '', s)

    if not s:
        return ("", "")

    primary = []
    alternate = []
    current = 0
    length = len(s)
    last = length - 1

    # Skip certain initial letter combinations
    if s[:2] in ['GN', 'KN', 'PN', 'WR', 'PS']:
        current = 1

    # Handle initial X
    if s[0] == 'X':
        primary.append('S')
        alternate.append('S')
        current = 1

    while current < length:
        char = s[current]

        # Vowels - only at beginning
        if char in 'AEIOU':
            if current == 0:
                primary.append('A')
                alternate.append('A')
            current += 1
            continue

        if char == 'B':
            primary.append('P')
            alternate.append('P')
            # Skip double B
            current += 2 if current + 1 < length and s[current + 1] == 'B' else 1

        elif char == 'C':
            if current + 1 < length:
                next_char = s[current + 1]
                if next_char == 'H':
                    primary.append('X')
                    alternate.append('X')
                    current += 2
                elif next_char in 'IEY':
                    primary.append('S')
                    alternate.append('S')
                    current += 2
                elif next_char == 'K':
                    primary.append('K')
                    alternate.append('K')
                    current += 2
                else:
                    primary.append('K')
                    alternate.append('K')
                    current += 1
            else:
                primary.append('K')
                alternate.append('K')
                current += 1

        elif char == 'D':
            if current + 1 < length and s[current + 1] == 'G':
                if current + 2 < length and s[current + 2] in 'IEY':
                    primary.append('J')
                    alternate.append('J')
                    current += 3
                else:
                    primary.append('TK')
                    alternate.append('TK')
                    current += 2
            else:
                primary.append('T')
                alternate.append('T')
                current += 1

        elif char == 'F':
            primary.append('F')
            alternate.append('F')
            current += 2 if current + 1 < length and s[current + 1] == 'F' else 1

        elif char == 'G':
            if current + 1 < length:
                next_char = s[current + 1]
                if next_char == 'H':
                    if current > 0 and s[current - 1] not in 'AEIOU':
                        current += 2
                        continue
                    primary.append('K')
                    alternate.append('K')
                    current += 2
                elif next_char == 'N':
                    current += 2
                elif next_char in 'IEY':
                    primary.append('J')
                    alternate.append('K')
                    current += 2
                else:
                    primary.append('K')
                    alternate.append('K')
                    current += 1
            else:
                primary.append('K')
                alternate.append('K')
                current += 1

        elif char == 'H':
            # H is silent after vowels or at end
            if current > 0 and s[current - 1] in 'AEIOU':
                current += 1
            elif current + 1 < length and s[current + 1] in 'AEIOU':
                primary.append('H')
                alternate.append('H')
                current += 1
            else:
                current += 1

        elif char == 'J':
            primary.append('J')
            alternate.append('H')
            current += 1

        elif char == 'K':
            primary.append('K')
            alternate.append('K')
            current += 2 if current + 1 < length and s[current + 1] == 'K' else 1

        elif char == 'L':
            primary.append('L')
            alternate.append('L')
            current += 2 if current + 1 < length and s[current + 1] == 'L' else 1

        elif char == 'M':
            primary.append('M')
            alternate.append('M')
            current += 2 if current + 1 < length and s[current + 1] == 'M' else 1

        elif char == 'N':
            primary.append('N')
            alternate.append('N')
            current += 2 if current + 1 < length and s[current + 1] == 'N' else 1

        elif char == 'P':
            if current + 1 < length and s[current + 1] == 'H':
                primary.append('F')
                alternate.append('F')
                current += 2
            else:
                primary.append('P')
                alternate.append('P')
                current += 2 if current + 1 < length and s[current + 1] == 'P' else 1

        elif char == 'Q':
            primary.append('K')
            alternate.append('K')
            current += 2 if current + 1 < length and s[current + 1] == 'U' else 1

        elif char == 'R':
            primary.append('R')
            alternate.append('R')
            current += 2 if current + 1 < length and s[current + 1] == 'R' else 1

        elif char == 'S':
            if current + 1 < length and s[current + 1] == 'H':
                primary.append('X')
                alternate.append('X')
                current += 2
            elif current + 2 < length and s[current:current + 3] in ['SIO', 'SIA']:
                primary.append('X')
                alternate.append('S')
                current += 3
            else:
                primary.append('S')
                alternate.append('S')
                current += 2 if current + 1 < length and s[current + 1] == 'S' else 1

        elif char == 'T':
            if current + 1 < length and s[current + 1] == 'H':
                primary.append('0')  # TH sound
                alternate.append('T')
                current += 2
            elif current + 2 < length and s[current:current + 3] in ['TIO', 'TIA']:
                primary.append('X')
                alternate.append('X')
                current += 3
            else:
                primary.append('T')
                alternate.append('T')
                current += 2 if current + 1 < length and s[current + 1] == 'T' else 1

        elif char == 'V':
            primary.append('F')
            alternate.append('F')
            current += 2 if current + 1 < length and s[current + 1] == 'V' else 1

        elif char == 'W':
            if current + 1 < length and s[current + 1] in 'AEIOU':
                primary.append('W')
                alternate.append('W')
            current += 1

        elif char == 'X':
            primary.append('KS')
            alternate.append('KS')
            current += 1

        elif char == 'Y':
            if current + 1 < length and s[current + 1] in 'AEIOU':
                primary.append('Y')
                alternate.append('Y')
            current += 1

        elif char == 'Z':
            primary.append('S')
            alternate.append('TS')
            current += 2 if current + 1 < length and s[current + 1] == 'Z' else 1

        else:
            current += 1

    return (''.join(primary)[:6], ''.join(alternate)[:6])


class FuzzyMatcher:
    """
    Fuzzy string matching service for entity auto-linking.

    Provides multiple matching strategies for finding similar strings:
    - Levenshtein distance (edit distance)
    - Jaro-Winkler similarity (good for short strings like names)
    - Token set ratio (handles different word order)
    - Phonetic matching (sounds-alike using Double Metaphone)

    Usage:
        matcher = FuzzyMatcher()

        # Normalize names for comparison
        normalized = matcher.normalize_name("John O'Brien")

        # Calculate similarity between strings
        score = matcher.calculate_similarity("John", "Jon")

        # Find similar names from a list
        matches = matcher.find_similar_names("Jon", ["John", "Jane", "Joan"])

        # Match entities with similar field values
        matches = matcher.match_entities_fuzzy(entities, "core.name.first_name")
    """

    def __init__(self, default_strategy: MatchStrategy = MatchStrategy.JARO_WINKLER):
        """
        Initialize the FuzzyMatcher.

        Args:
            default_strategy: Default matching strategy to use
        """
        if not RAPIDFUZZ_AVAILABLE:
            raise ImportError(
                "rapidfuzz is required for FuzzyMatcher. "
                "Install it with: pip install rapidfuzz"
            )

        self.default_strategy = default_strategy

        # Strategy function mapping
        self._strategy_funcs: Dict[MatchStrategy, Callable[[str, str], float]] = {
            MatchStrategy.LEVENSHTEIN: self._levenshtein_similarity,
            MatchStrategy.JARO_WINKLER: self._jaro_winkler_similarity,
            MatchStrategy.TOKEN_SET_RATIO: self._token_set_similarity,
            MatchStrategy.TOKEN_SORT_RATIO: self._token_sort_similarity,
            MatchStrategy.PARTIAL_RATIO: self._partial_similarity,
        }

    def normalize_name(self, name: str) -> str:
        """
        Normalize a name for comparison.

        Performs the following normalizations:
        - Convert to lowercase
        - Remove accents/diacritics (e.g., cafe -> cafe)
        - Remove special characters except spaces
        - Collapse multiple spaces
        - Strip leading/trailing whitespace

        Args:
            name: The name to normalize

        Returns:
            Normalized name string
        """
        if not name:
            return ""

        # Convert to lowercase
        result = name.lower()

        # Normalize unicode (decompose accented characters)
        result = unicodedata.normalize('NFD', result)

        # Remove diacritical marks (accents)
        result = ''.join(
            char for char in result
            if unicodedata.category(char) != 'Mn'
        )

        # Remove special characters except spaces and hyphens
        # Keep letters, numbers, spaces, and hyphens
        result = re.sub(r"[^\w\s-]", "", result)

        # Replace hyphens with spaces for consistency
        result = result.replace("-", " ")

        # Collapse multiple spaces
        result = re.sub(r'\s+', ' ', result)

        # Strip whitespace
        result = result.strip()

        return result

    def calculate_similarity(
        self,
        str1: str,
        str2: str,
        strategy: Optional[MatchStrategy] = None,
        normalize: bool = True
    ) -> float:
        """
        Calculate similarity score between two strings.

        Args:
            str1: First string
            str2: Second string
            strategy: Matching strategy to use (defaults to instance default)
            normalize: Whether to normalize strings before comparison

        Returns:
            Similarity score between 0.0 (no match) and 1.0 (exact match)
        """
        if not str1 or not str2:
            return 0.0

        if normalize:
            str1 = self.normalize_name(str1)
            str2 = self.normalize_name(str2)

        # Check again after normalization (whitespace-only strings become empty)
        if not str1 or not str2:
            return 0.0

        # Exact match after normalization
        if str1 == str2:
            return 1.0

        strategy = strategy or self.default_strategy

        if strategy not in self._strategy_funcs:
            raise ValueError(f"Unknown strategy: {strategy}")

        return self._strategy_funcs[strategy](str1, str2)

    def _levenshtein_similarity(self, str1: str, str2: str) -> float:
        """Calculate Levenshtein-based similarity (normalized)."""
        return Levenshtein.normalized_similarity(str1, str2)

    def _jaro_winkler_similarity(self, str1: str, str2: str) -> float:
        """Calculate Jaro-Winkler similarity."""
        return JaroWinkler.normalized_similarity(str1, str2)

    def _token_set_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate token set ratio similarity.

        This compares the sets of tokens (words) in each string,
        which handles different word orders well.
        E.g., "John Michael Smith" vs "Smith, John M." would score high.
        """
        return fuzz.token_set_ratio(str1, str2) / 100.0

    def _token_sort_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate token sort ratio similarity.

        Sorts tokens alphabetically before comparison.
        """
        return fuzz.token_sort_ratio(str1, str2) / 100.0

    def _partial_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate partial ratio similarity.

        Good for when one string is a substring of another.
        """
        return fuzz.partial_ratio(str1, str2) / 100.0

    def phonetic_match(self, str1: str, str2: str) -> Tuple[bool, float]:
        """
        Check if two strings match phonetically (sound alike).

        Uses Double Metaphone algorithm to generate phonetic codes
        and compares them.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Tuple of (is_match, confidence)
            - is_match: True if phonetic codes match
            - confidence: 1.0 for primary match, 0.8 for alternate match, 0.0 for no match
        """
        if not str1 or not str2:
            return (False, 0.0)

        # Normalize for phonetic comparison
        s1 = self.normalize_name(str1)
        s2 = self.normalize_name(str2)

        if not s1 or not s2:
            return (False, 0.0)

        # Get phonetic codes
        primary1, alt1 = double_metaphone(s1)
        primary2, alt2 = double_metaphone(s2)

        # Check primary codes match
        if primary1 and primary2 and primary1 == primary2:
            return (True, 1.0)

        # Check alternate codes match
        if alt1 and alt2 and alt1 == alt2:
            return (True, 0.9)

        # Check cross-matches (primary1 == alt2 or alt1 == primary2)
        if primary1 and alt2 and primary1 == alt2:
            return (True, 0.85)
        if alt1 and primary2 and alt1 == primary2:
            return (True, 0.85)

        return (False, 0.0)

    def find_similar_names(
        self,
        name: str,
        candidates: List[str],
        threshold: float = 0.8,
        strategy: Optional[MatchStrategy] = None,
        include_phonetic: bool = True
    ) -> List[Tuple[str, float]]:
        """
        Find names similar to the given name from a list of candidates.

        Args:
            name: The name to find matches for
            candidates: List of candidate names to compare against
            threshold: Minimum similarity score (0.0-1.0) to include in results
            strategy: Matching strategy to use
            include_phonetic: Whether to include phonetic matches

        Returns:
            List of (candidate_name, similarity_score) tuples, sorted by score descending
        """
        if not name or not candidates:
            return []

        results = []
        normalized_name = self.normalize_name(name)

        if not normalized_name:
            return []

        for candidate in candidates:
            if not candidate:
                continue

            # Calculate fuzzy similarity
            similarity = self.calculate_similarity(
                name, candidate,
                strategy=strategy,
                normalize=True
            )

            # Check phonetic match if enabled
            if include_phonetic and similarity < threshold:
                is_phonetic_match, phonetic_score = self.phonetic_match(name, candidate)
                if is_phonetic_match:
                    # Use phonetic score if higher
                    similarity = max(similarity, phonetic_score)

            if similarity >= threshold:
                results.append((candidate, similarity))

        # Sort by similarity score descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def _extract_field_value(self, entity: Dict[str, Any], field_path: str) -> List[str]:
        """
        Extract field value(s) from an entity using a dot-notation path.

        Args:
            entity: Entity dictionary
            field_path: Dot-notation path (e.g., 'core.name.first_name')

        Returns:
            List of string values found at the path
        """
        parts = field_path.split('.')

        # Start with the profile or the entity itself
        current = entity.get('profile', entity)

        for i, part in enumerate(parts):
            if current is None:
                return []

            if isinstance(current, list):
                # Handle list of objects - extract from each
                values = []
                remaining_path = '.'.join(parts[i:])
                for item in current:
                    values.extend(self._extract_field_value(
                        {'profile': item} if isinstance(item, dict) else item,
                        remaining_path
                    ))
                return values

            if isinstance(current, dict):
                current = current.get(part)
            else:
                return []

        # Convert final value to list of strings
        if current is None:
            return []
        if isinstance(current, list):
            return [str(v) for v in current if v]
        return [str(current)] if current else []

    def match_entities_fuzzy(
        self,
        entities: List[Dict[str, Any]],
        field_path: str,
        threshold: float = 0.85,
        strategy: Optional[MatchStrategy] = None,
        include_phonetic: bool = True
    ) -> List[FuzzyMatch]:
        """
        Find entities with similar field values.

        Compares the specified field across all entities and returns
        pairs that have similarity above the threshold.

        Args:
            entities: List of entity dictionaries
            field_path: Dot-notation path to the field to compare
            threshold: Minimum similarity score to include
            strategy: Matching strategy to use
            include_phonetic: Whether to include phonetic matches

        Returns:
            List of FuzzyMatch objects representing similar entity pairs
        """
        if not entities or len(entities) < 2:
            return []

        # Extract values for each entity
        entity_values: List[Tuple[str, List[str]]] = []

        for entity in entities:
            entity_id = entity.get('id', '')
            if not entity_id:
                continue

            values = self._extract_field_value(entity, field_path)
            if values:
                entity_values.append((entity_id, values))

        # Compare all pairs
        matches = []
        processed_pairs = set()

        for i, (id1, values1) in enumerate(entity_values):
            for j, (id2, values2) in enumerate(entity_values):
                if i >= j:  # Skip self and already-processed pairs
                    continue

                pair_key = tuple(sorted([id1, id2]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                # Compare all value combinations
                for val1 in values1:
                    for val2 in values2:
                        if not val1 or not val2:
                            continue

                        # Exact match
                        normalized1 = self.normalize_name(val1)
                        normalized2 = self.normalize_name(val2)

                        if normalized1 == normalized2:
                            matches.append(FuzzyMatch(
                                entity1_id=id1,
                                entity2_id=id2,
                                field_path=field_path,
                                value1=val1,
                                value2=val2,
                                similarity=1.0,
                                match_type=MatchType.EXACT.value
                            ))
                            continue

                        # Fuzzy match
                        similarity = self.calculate_similarity(
                            val1, val2,
                            strategy=strategy,
                            normalize=True
                        )

                        match_type = MatchType.FUZZY

                        # Check phonetic match
                        if include_phonetic and similarity < threshold:
                            is_phonetic, phonetic_score = self.phonetic_match(val1, val2)
                            if is_phonetic and phonetic_score >= threshold:
                                similarity = phonetic_score
                                match_type = MatchType.PHONETIC

                        if similarity >= threshold:
                            matches.append(FuzzyMatch(
                                entity1_id=id1,
                                entity2_id=id2,
                                field_path=field_path,
                                value1=val1,
                                value2=val2,
                                similarity=similarity,
                                match_type=match_type.value
                            ))

        # Sort by similarity descending
        matches.sort(key=lambda m: m.similarity, reverse=True)

        return matches

    def calculate_combined_similarity(
        self,
        str1: str,
        str2: str,
        weights: Optional[Dict[MatchStrategy, float]] = None
    ) -> float:
        """
        Calculate a weighted combination of multiple similarity strategies.

        Args:
            str1: First string
            str2: Second string
            weights: Dictionary mapping strategies to weights (normalized automatically)

        Returns:
            Combined similarity score
        """
        if weights is None:
            weights = {
                MatchStrategy.JARO_WINKLER: 0.4,
                MatchStrategy.TOKEN_SET_RATIO: 0.3,
                MatchStrategy.LEVENSHTEIN: 0.3,
            }

        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.0

        weighted_sum = 0.0
        for strategy, weight in weights.items():
            score = self.calculate_similarity(str1, str2, strategy=strategy)
            weighted_sum += score * (weight / total_weight)

        return weighted_sum


# Module-level instance for convenience
_fuzzy_matcher_instance: Optional[FuzzyMatcher] = None


def get_fuzzy_matcher() -> FuzzyMatcher:
    """
    Get or create the FuzzyMatcher singleton instance.

    Returns:
        FuzzyMatcher instance
    """
    global _fuzzy_matcher_instance

    if _fuzzy_matcher_instance is None:
        _fuzzy_matcher_instance = FuzzyMatcher()

    return _fuzzy_matcher_instance

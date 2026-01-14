/**
 * Types for Smart Suggestions System
 * Based on Phase 43 API specification and Phase 46 UI design
 */

/**
 * Confidence levels for suggestions
 * Maps to color coding: HIGH=green, MEDIUM=amber, LOW=red
 */
export type ConfidenceLevel = 'high' | 'medium' | 'low';

/**
 * Match types supported by the suggestion system
 */
export type MatchType =
  | 'hash_match'      // Exact file/image hash match (1.0 confidence)
  | 'exact_string'    // Exact email/phone/crypto match (0.95 confidence)
  | 'fuzzy_match'     // Jaro-Winkler/Levenshtein similarity (0.3-0.9)
  | 'partial_match'   // Partial name/address match (0.3-0.9)
  | 'cross_entity';   // Found in multiple entities

/**
 * Suggestion status tracking
 */
export type SuggestionStatus =
  | 'pending'      // Awaiting user review
  | 'viewed'       // User has seen but not acted
  | 'linked'       // User linked the entities
  | 'merged'       // User merged the duplicates
  | 'dismissed';   // User dismissed the suggestion

/**
 * Match factor explaining why a match was suggested
 */
export interface MatchFactor {
  name: string;
  description: string;
  weight: number;
  score: number;
}

/**
 * Single suggestion for entity matching
 */
export interface Suggestion {
  id: string;
  entityId: string;
  matchedEntityId?: string;
  matchedOrphanId?: string;
  matchType: MatchType;
  matchValue: string;
  confidence: number;
  confidenceLevel: ConfidenceLevel;
  factors: MatchFactor[];
  status: SuggestionStatus;
  createdAt: string;
  updatedAt: string;
  // HATEOAS links
  _links: {
    self: { href: string };
    entity: { href: string };
    matchedEntity?: { href: string };
    link?: { href: string };
    merge?: { href: string };
    dismiss?: { href: string };
  };
}

/**
 * Summary of suggestions for an entity
 */
export interface SuggestionSummary {
  entityId: string;
  totalCount: number;
  highConfidenceCount: number;
  mediumConfidenceCount: number;
  lowConfidenceCount: number;
  pendingCount: number;
  lastUpdated: string;
}

/**
 * API response for suggestions list
 */
export interface SuggestionsResponse {
  entityId: string;
  suggestions: Suggestion[];
  summary: SuggestionSummary;
  _links: {
    self: { href: string };
    entity: { href: string };
    refresh?: { href: string };
  };
}

/**
 * WebSocket event types for real-time updates
 */
export type SuggestionEventType =
  | 'suggestion_generated'
  | 'suggestion_dismissed'
  | 'entity_merged'
  | 'data_linked'
  | 'orphan_linked';

/**
 * WebSocket event payload
 */
export interface SuggestionEvent {
  eventType: SuggestionEventType;
  timestamp: string;
  data: {
    entityId?: string;
    suggestionCount?: number;
    highConfidenceCount?: number;
    mediumConfidenceCount?: number;
    lowConfidenceCount?: number;
    affectedEntities?: string[];
    reason?: string;
  };
  _links?: {
    suggestions?: { href: string };
    entity?: { href: string };
  };
}

/**
 * Action result from link/merge/dismiss operations
 */
export interface ActionResult {
  success: boolean;
  actionId: string;
  message: string;
  affectedEntities: string[];
}

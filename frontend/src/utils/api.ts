import type { SuggestionsResponse, ActionResult } from '@/types';

/**
 * API client for suggestions endpoints
 * Based on Phase 44 REST API specification
 */

const API_BASE = '/api/v1';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.error || error.message || 'API request failed');
  }

  return response.json();
}

/**
 * Fetch suggestions for an entity
 */
export async function fetchEntitySuggestions(
  _projectId: string,
  entityId: string
): Promise<SuggestionsResponse> {
  return fetchApi<SuggestionsResponse>(
    `/suggestions/entity/${entityId}`
  );
}

/**
 * Compute fresh suggestions for an entity
 */
export async function computeSuggestions(
  _projectId: string,
  entityId: string
): Promise<SuggestionsResponse> {
  return fetchApi<SuggestionsResponse>(
    `/suggestions/entity/${entityId}/refresh`,
    { method: 'POST' }
  );
}

/**
 * Dismiss a suggestion
 */
export async function dismissSuggestion(
  _projectId: string,
  entityId: string,
  suggestionId: string,
  reason: string
): Promise<ActionResult> {
  return fetchApi<ActionResult>(
    `/suggestions/${suggestionId}/dismiss?entity_id=${encodeURIComponent(entityId)}`,
    {
      method: 'POST',
      body: JSON.stringify({
        reason,
      }),
    }
  );
}

/**
 * Link two entities
 */
export async function linkEntities(
  _projectId: string,
  entityId1: string,
  entityId2: string,
  relationshipType: string,
  reason: string,
  confidence?: string
): Promise<ActionResult> {
  return fetchApi<ActionResult>(
    `/suggestions/linking/create-relationship`,
    {
      method: 'POST',
      body: JSON.stringify({
        entity_id_1: entityId1,
        entity_id_2: entityId2,
        relationship_type: relationshipType,
        reason,
        confidence,
      }),
    }
  );
}

/**
 * Merge two entities
 */
export async function mergeEntities(
  _projectId: string,
  entityId1: string,
  entityId2: string,
  keepEntityId: string,
  reason: string
): Promise<ActionResult> {
  return fetchApi<ActionResult>(
    `/suggestions/linking/merge-entities`,
    {
      method: 'POST',
      body: JSON.stringify({
        entity_id_1: entityId1,
        entity_id_2: entityId2,
        keep_entity_id: keepEntityId,
        reason,
      }),
    }
  );
}

/**
 * Link data items
 */
export async function linkDataItems(
  _projectId: string,
  dataId1: string,
  dataId2: string,
  reason: string,
  confidence?: number
): Promise<ActionResult> {
  return fetchApi<ActionResult>(
    `/suggestions/linking/data-items`,
    {
      method: 'POST',
      body: JSON.stringify({
        data_id_1: dataId1,
        data_id_2: dataId2,
        reason,
        confidence,
      }),
    }
  );
}

/**
 * Link orphan to entity
 */
export async function linkOrphanToEntity(
  _projectId: string,
  orphanId: string,
  entityId: string,
  reason: string
): Promise<ActionResult> {
  return fetchApi<ActionResult>(
    `/suggestions/linking/orphan-to-entity`,
    {
      method: 'POST',
      body: JSON.stringify({
        orphan_id: orphanId,
        entity_id: entityId,
        reason,
      }),
    }
  );
}

/**
 * Fetch suggestion summary for multiple entities
 */
export async function fetchProjectSuggestionsSummary(
  _projectId: string
): Promise<{ entities: Array<{ entityId: string; summary: { totalCount: number; highConfidenceCount: number } }> }> {
  return fetchApi(`/suggestions/summary`);
}

import { useEffect, useCallback } from 'react';
import type { Suggestion } from '@/types';
import { SuggestionCard } from './SuggestionCard';
import { SuggestionBadge } from './SuggestionBadge';
import {
  useSuggestionsStore,
  selectSuggestions,
  selectSummary,
  selectIsLoading,
  selectError,
} from '@/store';
import { useWebSocket } from '@/hooks';
import { dismissSuggestion as apiDismissSuggestion, linkEntities, mergeEntities } from '@/utils/api';
import { getConfidenceLevel } from '@/utils';

/**
 * SuggestionPanel Component
 *
 * Container component that displays all suggestions for an entity
 * with filtering, sorting, and real-time updates.
 */

export interface SuggestionPanelProps {
  /** Project ID */
  projectId: string;
  /** Entity ID to show suggestions for */
  entityId: string;
  /** Called when user wants to view an entity profile */
  onViewEntity?: (entityId: string) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Panel styles
 */
const styles: Record<string, React.CSSProperties> = {
  panel: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E5E7EB',
    borderRadius: '8px',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px',
    borderBottom: '1px solid #E5E7EB',
    backgroundColor: '#F9FAFB',
  },
  title: {
    fontSize: '16px',
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  counts: {
    display: 'flex',
    gap: '8px',
  },
  refreshButton: {
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #E5E7EB',
    backgroundColor: '#FFFFFF',
    cursor: 'pointer',
    fontSize: '13px',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  body: {
    padding: '16px',
    maxHeight: '600px',
    overflowY: 'auto' as const,
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px',
    color: '#6B7280',
  },
  error: {
    padding: '16px',
    backgroundColor: '#FEE2E2',
    color: '#991B1B',
    borderRadius: '6px',
    margin: '16px',
  },
  empty: {
    textAlign: 'center' as const,
    padding: '40px',
    color: '#6B7280',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '12px',
  },
  connectionStatus: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    color: '#6B7280',
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
};

export function SuggestionPanel({
  projectId,
  entityId,
  onViewEntity,
  className = '',
}: SuggestionPanelProps) {
  // Store selectors
  const suggestions = useSuggestionsStore(selectSuggestions(entityId));
  const summary = useSuggestionsStore(selectSummary(entityId));
  const isLoading = useSuggestionsStore(selectIsLoading(entityId));
  const error = useSuggestionsStore(selectError(entityId));

  // Store actions
  const fetchSuggestions = useSuggestionsStore((s) => s.fetchSuggestions);
  const refreshSuggestions = useSuggestionsStore((s) => s.refreshSuggestions);
  const dismissSuggestionLocal = useSuggestionsStore((s) => s.dismissSuggestion);
  const clearError = useSuggestionsStore((s) => s.clearError);
  const setExpandedSuggestion = useSuggestionsStore((s) => s.setExpandedSuggestion);
  const expandedSuggestionId = useSuggestionsStore((s) => s.expandedSuggestionId);

  // WebSocket connection
  const { state: wsState, subscribeToEntity, unsubscribeFromEntity } = useWebSocket({
    projectId,
  });

  // Fetch suggestions on mount
  useEffect(() => {
    fetchSuggestions(projectId, entityId);
  }, [projectId, entityId, fetchSuggestions]);

  // Subscribe to entity-specific updates
  useEffect(() => {
    if (wsState === 'connected') {
      subscribeToEntity(entityId);
      return () => unsubscribeFromEntity(entityId);
    }
  }, [wsState, entityId, subscribeToEntity, unsubscribeFromEntity]);

  // Handlers
  const handleRefresh = useCallback(() => {
    refreshSuggestions(projectId, entityId);
  }, [projectId, entityId, refreshSuggestions]);

  const handleDismiss = useCallback(
    async (suggestion: Suggestion, reason: string) => {
      try {
        const dataId = suggestion.matchedOrphanId || suggestion.id;
        await apiDismissSuggestion(projectId, entityId, dataId, reason);
        dismissSuggestionLocal(entityId, suggestion.id);
      } catch (err) {
        console.error('Failed to dismiss suggestion:', err);
      }
    },
    [projectId, entityId, dismissSuggestionLocal]
  );

  const handleLink = useCallback(
    async (suggestion: Suggestion) => {
      if (!suggestion.matchedEntityId) return;

      const reason = prompt('Reason for linking these entities:');
      if (!reason) return;

      try {
        await linkEntities(
          projectId,
          entityId,
          suggestion.matchedEntityId,
          'RELATED_TO',
          reason
        );
        dismissSuggestionLocal(entityId, suggestion.id);
      } catch (err) {
        console.error('Failed to link entities:', err);
      }
    },
    [projectId, entityId, dismissSuggestionLocal]
  );

  const handleMerge = useCallback(
    async (suggestion: Suggestion) => {
      if (!suggestion.matchedEntityId) return;

      const confirmMerge = confirm(
        'This will merge these two entities. This action cannot be undone. Continue?'
      );
      if (!confirmMerge) return;

      const reason = prompt('Reason for merging these entities:');
      if (!reason) return;

      try {
        await mergeEntities(
          projectId,
          entityId,
          suggestion.matchedEntityId,
          entityId, // Keep current entity
          reason
        );
        dismissSuggestionLocal(entityId, suggestion.id);
        // Refresh to show updated state
        handleRefresh();
      } catch (err) {
        console.error('Failed to merge entities:', err);
      }
    },
    [projectId, entityId, dismissSuggestionLocal, handleRefresh]
  );

  const handleViewProfile = useCallback(
    (suggestion: Suggestion) => {
      const targetId = suggestion.matchedEntityId || suggestion.matchedOrphanId;
      if (targetId) {
        onViewEntity?.(targetId);
      }
    },
    [onViewEntity]
  );

  // Sort suggestions by confidence (highest first)
  const sortedSuggestions = [...suggestions].sort(
    (a, b) => b.confidence - a.confidence
  );

  // WebSocket status indicator
  const getStatusColor = () => {
    switch (wsState) {
      case 'connected':
        return '#10B981';
      case 'connecting':
        return '#F59E0B';
      case 'error':
        return '#EF4444';
      default:
        return '#9CA3AF';
    }
  };

  return (
    <div className={`suggestion-panel ${className}`} style={styles.panel}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.title}>
          <span>💡 Suggested Matches</span>
          {summary && (
            <span style={{ fontSize: '14px', fontWeight: 400, color: '#6B7280' }}>
              ({summary.totalCount} total)
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Confidence counts */}
          {summary && (
            <div style={styles.counts}>
              {summary.highConfidenceCount > 0 && (
                <SuggestionBadge
                  level="high"
                  score={0.95}
                  variant="compact"
                  showScore={false}
                  showIcon={false}
                />
              )}
              {summary.mediumConfidenceCount > 0 && (
                <SuggestionBadge
                  level="medium"
                  score={0.75}
                  variant="compact"
                  showScore={false}
                  showIcon={false}
                />
              )}
              {summary.lowConfidenceCount > 0 && (
                <SuggestionBadge
                  level="low"
                  score={0.55}
                  variant="compact"
                  showScore={false}
                  showIcon={false}
                />
              )}
            </div>
          )}

          {/* Connection status */}
          <div style={styles.connectionStatus}>
            <div
              style={{
                ...styles.statusDot,
                backgroundColor: getStatusColor(),
              }}
            />
            <span>{wsState === 'connected' ? 'Live' : wsState}</span>
          </div>

          {/* Refresh button */}
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            style={{
              ...styles.refreshButton,
              opacity: isLoading ? 0.5 : 1,
              cursor: isLoading ? 'not-allowed' : 'pointer',
            }}
          >
            <span style={{ transform: isLoading ? 'rotate(360deg)' : 'none' }}>🔄</span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div style={styles.error}>
          <strong>Error:</strong> {error}
          <button
            onClick={() => clearError(entityId)}
            style={{
              marginLeft: '12px',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#991B1B',
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Body */}
      <div style={styles.body}>
        {/* Loading state */}
        {isLoading && suggestions.length === 0 && (
          <div style={styles.loading}>
            <span>Loading suggestions...</span>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && suggestions.length === 0 && (
          <div style={styles.empty}>
            <div style={styles.emptyIcon}>✓</div>
            <div style={{ fontWeight: 500, marginBottom: '8px' }}>
              No suggestions found
            </div>
            <div style={{ fontSize: '13px' }}>
              This entity has no pending match suggestions.
            </div>
          </div>
        )}

        {/* Suggestion cards */}
        {sortedSuggestions.map((suggestion) => (
          <SuggestionCard
            key={suggestion.id}
            suggestion={suggestion}
            onDismiss={handleDismiss}
            onLink={handleLink}
            onMerge={handleMerge}
            onViewProfile={handleViewProfile}
            isExpanded={expandedSuggestionId === suggestion.id}
            onExpandChange={(expanded) =>
              setExpandedSuggestion(expanded ? suggestion.id : null)
            }
          />
        ))}
      </div>
    </div>
  );
}

export default SuggestionPanel;

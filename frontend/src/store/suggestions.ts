import { create } from 'zustand';
import type { Suggestion, SuggestionSummary, SuggestionEvent } from '@/types';
import { fetchEntitySuggestions, computeSuggestions } from '@/utils/api';

/**
 * Suggestions store state
 */
interface SuggestionsState {
  // Data
  suggestions: Record<string, Suggestion[]>; // entityId -> suggestions
  summaries: Record<string, SuggestionSummary>; // entityId -> summary

  // Loading states
  loading: Record<string, boolean>; // entityId -> loading
  errors: Record<string, string | null>; // entityId -> error

  // UI state
  expandedSuggestionId: string | null;
  selectedEntityId: string | null;

  // Actions
  fetchSuggestions: (projectId: string, entityId: string) => Promise<void>;
  refreshSuggestions: (projectId: string, entityId: string) => Promise<void>;
  dismissSuggestion: (entityId: string, suggestionId: string) => void;
  markSuggestionViewed: (entityId: string, suggestionId: string) => void;
  setExpandedSuggestion: (suggestionId: string | null) => void;
  setSelectedEntity: (entityId: string | null) => void;
  handleWebSocketEvent: (event: SuggestionEvent) => void;
  clearError: (entityId: string) => void;
}

/**
 * Zustand store for suggestions state management
 */
export const useSuggestionsStore = create<SuggestionsState>((set, get) => ({
  // Initial state
  suggestions: {},
  summaries: {},
  loading: {},
  errors: {},
  expandedSuggestionId: null,
  selectedEntityId: null,

  // Fetch suggestions for an entity
  fetchSuggestions: async (projectId: string, entityId: string) => {
    set((state) => ({
      loading: { ...state.loading, [entityId]: true },
      errors: { ...state.errors, [entityId]: null },
    }));

    try {
      const response = await fetchEntitySuggestions(projectId, entityId);
      set((state) => ({
        suggestions: { ...state.suggestions, [entityId]: response.suggestions },
        summaries: { ...state.summaries, [entityId]: response.summary },
        loading: { ...state.loading, [entityId]: false },
      }));
    } catch (error) {
      set((state) => ({
        loading: { ...state.loading, [entityId]: false },
        errors: { ...state.errors, [entityId]: (error as Error).message },
      }));
    }
  },

  // Compute fresh suggestions
  refreshSuggestions: async (projectId: string, entityId: string) => {
    set((state) => ({
      loading: { ...state.loading, [entityId]: true },
      errors: { ...state.errors, [entityId]: null },
    }));

    try {
      const response = await computeSuggestions(projectId, entityId);
      set((state) => ({
        suggestions: { ...state.suggestions, [entityId]: response.suggestions },
        summaries: { ...state.summaries, [entityId]: response.summary },
        loading: { ...state.loading, [entityId]: false },
      }));
    } catch (error) {
      set((state) => ({
        loading: { ...state.loading, [entityId]: false },
        errors: { ...state.errors, [entityId]: (error as Error).message },
      }));
    }
  },

  // Remove dismissed suggestion from UI
  dismissSuggestion: (entityId: string, suggestionId: string) => {
    set((state) => {
      const entitySuggestions = state.suggestions[entityId] || [];
      return {
        suggestions: {
          ...state.suggestions,
          [entityId]: entitySuggestions.filter((s) => s.id !== suggestionId),
        },
        // Update summary counts
        summaries: {
          ...state.summaries,
          [entityId]: state.summaries[entityId]
            ? {
                ...state.summaries[entityId],
                totalCount: state.summaries[entityId].totalCount - 1,
                pendingCount: state.summaries[entityId].pendingCount - 1,
              }
            : state.summaries[entityId],
        },
      };
    });
  },

  // Mark suggestion as viewed
  markSuggestionViewed: (entityId: string, suggestionId: string) => {
    set((state) => {
      const entitySuggestions = state.suggestions[entityId] || [];
      return {
        suggestions: {
          ...state.suggestions,
          [entityId]: entitySuggestions.map((s) =>
            s.id === suggestionId && s.status === 'pending'
              ? { ...s, status: 'viewed' as const }
              : s
          ),
        },
      };
    });
  },

  // Toggle expanded suggestion
  setExpandedSuggestion: (suggestionId: string | null) => {
    set({ expandedSuggestionId: suggestionId });
  },

  // Select entity for suggestion viewing
  setSelectedEntity: (entityId: string | null) => {
    set({ selectedEntityId: entityId });
  },

  // Handle real-time WebSocket events
  handleWebSocketEvent: (event: SuggestionEvent) => {
    const { eventType, data } = event;

    switch (eventType) {
      case 'suggestion_generated':
        // Update summary with new counts
        if (data.entityId) {
          set((state) => ({
            summaries: {
              ...state.summaries,
              [data.entityId!]: {
                entityId: data.entityId!,
                totalCount: data.suggestionCount || 0,
                highConfidenceCount: data.highConfidenceCount || 0,
                mediumConfidenceCount: data.mediumConfidenceCount || 0,
                lowConfidenceCount: data.lowConfidenceCount || 0,
                pendingCount: data.suggestionCount || 0,
                lastUpdated: event.timestamp,
              },
            },
          }));
        }
        break;

      case 'suggestion_dismissed':
        if (data.entityId) {
          // Suggestion already removed via dismissSuggestion action
          // This handles remote dismissals (from another client)
          get().dismissSuggestion(data.entityId, data.entityId);
        }
        break;

      case 'entity_merged':
      case 'data_linked':
      case 'orphan_linked':
        // Invalidate affected entities' suggestions
        if (data.affectedEntities) {
          data.affectedEntities.forEach((entityId) => {
            set((state) => ({
              suggestions: { ...state.suggestions, [entityId]: [] },
              summaries: { ...state.summaries, [entityId]: undefined as unknown as SuggestionSummary },
            }));
          });
        }
        break;
    }
  },

  // Clear error for entity
  clearError: (entityId: string) => {
    set((state) => ({
      errors: { ...state.errors, [entityId]: null },
    }));
  },
}));

/**
 * Selector hooks for common patterns
 */
export const selectSuggestions = (entityId: string) => (state: SuggestionsState) =>
  state.suggestions[entityId] || [];

export const selectSummary = (entityId: string) => (state: SuggestionsState) =>
  state.summaries[entityId];

export const selectIsLoading = (entityId: string) => (state: SuggestionsState) =>
  state.loading[entityId] || false;

export const selectError = (entityId: string) => (state: SuggestionsState) =>
  state.errors[entityId];

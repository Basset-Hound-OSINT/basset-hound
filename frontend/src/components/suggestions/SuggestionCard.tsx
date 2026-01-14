import { useState, useCallback } from 'react';
import type { Suggestion, MatchFactor } from '@/types';
import { SuggestionBadge } from './SuggestionBadge';
import { CONFIDENCE_COLORS, formatConfidence } from '@/utils';

/**
 * SuggestionCard Component
 *
 * Displays a single suggestion with expandable details and action buttons.
 * Based on UI-COMPONENTS-SPECIFICATION.md Component 1: Suggestion Card.
 */

export interface SuggestionCardProps {
  /** The suggestion data */
  suggestion: Suggestion;
  /** Called when user clicks dismiss */
  onDismiss?: (suggestion: Suggestion, reason: string) => void;
  /** Called when user clicks link entities */
  onLink?: (suggestion: Suggestion) => void;
  /** Called when user clicks merge duplicates */
  onMerge?: (suggestion: Suggestion) => void;
  /** Called when user clicks view profile */
  onViewProfile?: (suggestion: Suggestion) => void;
  /** Whether this card is expanded */
  isExpanded?: boolean;
  /** Called when expansion state changes */
  onExpandChange?: (expanded: boolean) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Match factor row component
 */
function MatchFactorRow({ factor }: { factor: MatchFactor }) {
  return (
    <div className="suggestion-card__factor" style={factorRowStyle}>
      <span className="suggestion-card__factor-check" style={{ color: '#10B981' }}>
        ✓
      </span>
      <span className="suggestion-card__factor-name" style={{ flex: 1 }}>
        {factor.name}
      </span>
      <span className="suggestion-card__factor-score" style={{ color: '#6B7280', fontSize: '12px' }}>
        (Weight: {factor.weight.toFixed(1)}, Score: {factor.score.toFixed(2)})
      </span>
    </div>
  );
}

const factorRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '4px 0',
  fontSize: '13px',
};

/**
 * Card styles (inline for standalone use)
 */
const cardStyles: Record<string, React.CSSProperties> = {
  card: {
    border: '1px solid #E5E7EB',
    borderRadius: '8px',
    backgroundColor: '#FFFFFF',
    overflow: 'hidden',
    marginBottom: '12px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    borderBottom: '1px solid #E5E7EB',
  },
  body: {
    padding: '16px',
  },
  matchInfo: {
    fontSize: '14px',
    marginBottom: '12px',
  },
  matchValue: {
    fontWeight: 600,
    fontFamily: 'monospace',
  },
  arrow: {
    color: '#9CA3AF',
    margin: '4px 0',
  },
  target: {
    color: '#6B7280',
    fontSize: '13px',
  },
  divider: {
    borderTop: '1px dashed #E5E7EB',
    margin: '12px 0',
  },
  expandButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#3B82F6',
    fontSize: '13px',
    padding: '4px 0',
  },
  factorsSection: {
    marginTop: '12px',
    padding: '12px',
    backgroundColor: '#F9FAFB',
    borderRadius: '6px',
  },
  factorsTitle: {
    fontWeight: 600,
    fontSize: '13px',
    marginBottom: '8px',
  },
  totalScore: {
    marginTop: '12px',
    paddingTop: '8px',
    borderTop: '1px solid #E5E7EB',
    fontSize: '13px',
  },
  lastUpdated: {
    color: '#9CA3AF',
    fontSize: '12px',
    marginTop: '8px',
  },
  footer: {
    display: 'flex',
    gap: '8px',
    padding: '12px 16px',
    borderTop: '1px solid #E5E7EB',
    backgroundColor: '#F9FAFB',
  },
  button: {
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    border: '1px solid #E5E7EB',
    backgroundColor: '#FFFFFF',
    transition: 'background-color 0.15s',
  },
  buttonPrimary: {
    backgroundColor: '#3B82F6',
    color: '#FFFFFF',
    border: '1px solid #3B82F6',
  },
  buttonDanger: {
    color: '#DC2626',
    borderColor: '#DC2626',
  },
  dismissButton: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#9CA3AF',
    fontSize: '18px',
    padding: '4px',
    lineHeight: 1,
  },
};

export function SuggestionCard({
  suggestion,
  onDismiss,
  onLink,
  onMerge,
  onViewProfile,
  isExpanded: controlledExpanded,
  onExpandChange,
  className = '',
}: SuggestionCardProps) {
  const [internalExpanded, setInternalExpanded] = useState(false);
  const [dismissReason, setDismissReason] = useState('');
  const [showDismissInput, setShowDismissInput] = useState(false);

  // Support both controlled and uncontrolled expansion
  const isExpanded = controlledExpanded ?? internalExpanded;
  const setExpanded = onExpandChange ?? setInternalExpanded;

  const colors = CONFIDENCE_COLORS[suggestion.confidenceLevel];

  const handleDismiss = useCallback(() => {
    if (showDismissInput && dismissReason.trim()) {
      onDismiss?.(suggestion, dismissReason.trim());
      setShowDismissInput(false);
      setDismissReason('');
    } else {
      setShowDismissInput(true);
    }
  }, [suggestion, onDismiss, dismissReason, showDismissInput]);

  const handleCancelDismiss = useCallback(() => {
    setShowDismissInput(false);
    setDismissReason('');
  }, []);

  const formatMatchType = (type: string): string => {
    const labels: Record<string, string> = {
      hash_match: 'Hash Match',
      exact_string: 'Exact Match',
      fuzzy_match: 'Fuzzy Match',
      partial_match: 'Partial Match',
      cross_entity: 'Cross-Entity Match',
    };
    return labels[type] || type;
  };

  const getTimeSince = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const diff = now.getTime() - then.getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    const days = Math.floor(hours / 24);
    return `${days} day${days !== 1 ? 's' : ''} ago`;
  };

  return (
    <div
      className={`suggestion-card suggestion-card--${suggestion.confidenceLevel} ${className}`}
      style={{
        ...cardStyles.card,
        borderColor: colors.border,
      }}
    >
      {/* Header */}
      <div
        style={{
          ...cardStyles.header,
          backgroundColor: colors.background,
        }}
      >
        <SuggestionBadge
          level={suggestion.confidenceLevel}
          score={suggestion.confidence}
        />
        <button
          onClick={() => setShowDismissInput(true)}
          style={cardStyles.dismissButton}
          title="Dismiss suggestion"
          aria-label="Dismiss suggestion"
        >
          ✕
        </button>
      </div>

      {/* Body */}
      <div style={cardStyles.body}>
        {/* Match information */}
        <div style={cardStyles.matchInfo}>
          <div>
            <span style={{ color: '#6B7280' }}>{formatMatchType(suggestion.matchType)}: </span>
            <span style={cardStyles.matchValue}>{suggestion.matchValue}</span>
          </div>
          <div style={cardStyles.arrow}>↓</div>
          <div style={cardStyles.target}>
            Found in: {suggestion.matchedEntityId || suggestion.matchedOrphanId || 'Unknown'}
          </div>
        </div>

        <div style={cardStyles.divider} />

        {/* Why this match? */}
        <button
          onClick={() => setExpanded(!isExpanded)}
          style={cardStyles.expandButton}
        >
          <span>ℹ️</span>
          <span>Why this match?</span>
          <span>{isExpanded ? '▲' : '▼'}</span>
        </button>

        {/* Expanded details */}
        {isExpanded && suggestion.factors.length > 0 && (
          <div style={cardStyles.factorsSection}>
            <div style={cardStyles.factorsTitle}>Match Factors:</div>
            {suggestion.factors.map((factor, index) => (
              <MatchFactorRow key={index} factor={factor} />
            ))}
            <div style={cardStyles.totalScore}>
              <strong>Total Score:</strong> {formatConfidence(suggestion.confidence)} (weighted average)
            </div>
            <div style={cardStyles.lastUpdated}>
              Last Updated: {getTimeSince(suggestion.updatedAt)}
            </div>
          </div>
        )}

        {/* Dismiss reason input */}
        {showDismissInput && (
          <div style={{ marginTop: '12px' }}>
            <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px', color: '#374151' }}>
              Reason for dismissal (required):
            </label>
            <input
              type="text"
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              placeholder="e.g., Different person - verified via other identifiers"
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #D1D5DB',
                borderRadius: '6px',
                fontSize: '13px',
              }}
              autoFocus
            />
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <button
                onClick={handleDismiss}
                disabled={!dismissReason.trim()}
                style={{
                  ...cardStyles.button,
                  ...(dismissReason.trim() ? cardStyles.buttonDanger : { opacity: 0.5, cursor: 'not-allowed' }),
                }}
              >
                Dismiss
              </button>
              <button onClick={handleCancelDismiss} style={cardStyles.button}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer actions */}
      {!showDismissInput && (
        <div style={cardStyles.footer}>
          <button
            onClick={() => onViewProfile?.(suggestion)}
            style={cardStyles.button}
          >
            View Profile
          </button>
          <button
            onClick={() => onLink?.(suggestion)}
            style={cardStyles.button}
          >
            Link Entities
          </button>
          <button
            onClick={() => onMerge?.(suggestion)}
            style={{ ...cardStyles.button, ...cardStyles.buttonPrimary }}
          >
            Merge Duplicates
          </button>
        </div>
      )}
    </div>
  );
}

export default SuggestionCard;

import { type ConfidenceLevel } from '@/types';
import {
  CONFIDENCE_BADGES,
  CONFIDENCE_ICONS,
  CONFIDENCE_COLORS,
  getConfidenceLabel,
  formatConfidence,
} from '@/utils';

/**
 * SuggestionBadge Component
 *
 * Displays a confidence level badge with color coding and accessibility features.
 * Based on UI-COMPONENTS-SPECIFICATION.md Color System.
 */

export interface SuggestionBadgeProps {
  /** Confidence level (high/medium/low) */
  level: ConfidenceLevel;
  /** Numeric confidence score (0.0 - 1.0) */
  score: number;
  /** Display variant */
  variant?: 'badge' | 'pill' | 'compact';
  /** Show numeric score */
  showScore?: boolean;
  /** Show accessibility icon */
  showIcon?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * CSS styles for the badge (inline for standalone use)
 */
const styles = {
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 600,
    lineHeight: 1,
    whiteSpace: 'nowrap' as const,
  },
  pill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '2px 10px',
    borderRadius: '9999px',
    fontSize: '11px',
    fontWeight: 600,
    lineHeight: 1.2,
    whiteSpace: 'nowrap' as const,
  },
  compact: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '2px',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 600,
    lineHeight: 1,
    whiteSpace: 'nowrap' as const,
  },
};

export function SuggestionBadge({
  level,
  score,
  variant = 'badge',
  showScore = true,
  showIcon = true,
  className = '',
}: SuggestionBadgeProps) {
  const colors = CONFIDENCE_COLORS[level];
  const emoji = CONFIDENCE_BADGES[level];
  const icon = CONFIDENCE_ICONS[level];
  const label = getConfidenceLabel(level);
  const scoreText = formatConfidence(score);

  const baseStyle = styles[variant];
  const colorStyle = {
    backgroundColor: colors.background,
    color: colors.text,
    border: `1px solid ${colors.border}`,
  };

  return (
    <span
      className={`suggestion-badge suggestion-badge--${level} suggestion-badge--${variant} ${className}`}
      style={{ ...baseStyle, ...colorStyle }}
      role="status"
      aria-label={`${label}: ${scoreText}`}
    >
      {/* Emoji indicator (visual) */}
      <span aria-hidden="true">{emoji}</span>

      {/* Accessibility icon (for colorblind users) */}
      {showIcon && (
        <span className="suggestion-badge__icon" aria-hidden="true">
          {icon}
        </span>
      )}

      {/* Label text */}
      {variant !== 'compact' && (
        <span className="suggestion-badge__label">{label.toUpperCase()}</span>
      )}

      {/* Score */}
      {showScore && (
        <span className="suggestion-badge__score">({scoreText})</span>
      )}
    </span>
  );
}

export default SuggestionBadge;

import type { ConfidenceLevel } from '@/types';

/**
 * Confidence level thresholds
 * Based on Phase 43 matching algorithm
 */
export const CONFIDENCE_THRESHOLDS = {
  high: 0.9,
  medium: 0.7,
  low: 0.5,
} as const;

/**
 * Color system from UI-COMPONENTS-SPECIFICATION.md
 * Using Tailwind color palette
 */
export const CONFIDENCE_COLORS = {
  high: {
    primary: '#10B981',   // Green-500
    hover: '#059669',     // Green-600
    background: '#D1FAE5', // Green-100
    border: '#6EE7B7',    // Green-300
    text: '#065F46',      // Green-800
  },
  medium: {
    primary: '#F59E0B',   // Amber-500
    hover: '#D97706',     // Amber-600
    background: '#FEF3C7', // Amber-100
    border: '#FCD34D',    // Amber-300
    text: '#92400E',      // Amber-800
  },
  low: {
    primary: '#EF4444',   // Red-500
    hover: '#DC2626',     // Red-600
    background: '#FEE2E2', // Red-100
    border: '#FCA5A5',    // Red-300
    text: '#991B1B',      // Red-800
  },
} as const;

/**
 * Badge indicators for confidence levels
 */
export const CONFIDENCE_BADGES = {
  high: '🟢',
  medium: '🟡',
  low: '🔴',
} as const;

/**
 * Icons for accessibility (colorblind friendly)
 */
export const CONFIDENCE_ICONS = {
  high: '✓',    // Checkmark
  medium: '⚠',  // Warning
  low: 'ℹ️',    // Info
} as const;

/**
 * Get confidence level from numeric score
 */
export function getConfidenceLevel(score: number): ConfidenceLevel {
  if (score >= CONFIDENCE_THRESHOLDS.high) return 'high';
  if (score >= CONFIDENCE_THRESHOLDS.medium) return 'medium';
  return 'low';
}

/**
 * Get human-readable confidence label
 */
export function getConfidenceLabel(level: ConfidenceLevel): string {
  const labels: Record<ConfidenceLevel, string> = {
    high: 'High Confidence',
    medium: 'Medium Confidence',
    low: 'Low Confidence',
  };
  return labels[level];
}

/**
 * Format confidence score as percentage
 */
export function formatConfidence(score: number): string {
  return `${(score * 100).toFixed(0)}%`;
}

/**
 * Get CSS class names for confidence level
 * Compatible with both Tailwind and custom CSS
 */
export function getConfidenceClasses(level: ConfidenceLevel): {
  container: string;
  badge: string;
  text: string;
} {
  const classMap: Record<ConfidenceLevel, { container: string; badge: string; text: string }> = {
    high: {
      container: 'bg-green-100 border-green-300',
      badge: 'bg-green-500 text-white',
      text: 'text-green-800',
    },
    medium: {
      container: 'bg-amber-100 border-amber-300',
      badge: 'bg-amber-500 text-white',
      text: 'text-amber-800',
    },
    low: {
      container: 'bg-red-100 border-red-300',
      badge: 'bg-red-500 text-white',
      text: 'text-red-800',
    },
  };
  return classMap[level];
}

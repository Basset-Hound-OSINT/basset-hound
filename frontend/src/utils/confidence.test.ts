import { describe, it, expect } from 'vitest';
import {
  getConfidenceLevel,
  getConfidenceLabel,
  formatConfidence,
  getConfidenceClasses,
  CONFIDENCE_THRESHOLDS,
  CONFIDENCE_COLORS,
  CONFIDENCE_BADGES,
} from './confidence';

describe('confidence utilities', () => {
  describe('getConfidenceLevel', () => {
    it('returns high for scores >= 0.9', () => {
      expect(getConfidenceLevel(0.9)).toBe('high');
      expect(getConfidenceLevel(0.95)).toBe('high');
      expect(getConfidenceLevel(1.0)).toBe('high');
    });

    it('returns medium for scores >= 0.7 and < 0.9', () => {
      expect(getConfidenceLevel(0.7)).toBe('medium');
      expect(getConfidenceLevel(0.8)).toBe('medium');
      expect(getConfidenceLevel(0.89)).toBe('medium');
    });

    it('returns low for scores < 0.7', () => {
      expect(getConfidenceLevel(0.5)).toBe('low');
      expect(getConfidenceLevel(0.69)).toBe('low');
      expect(getConfidenceLevel(0.0)).toBe('low');
    });
  });

  describe('getConfidenceLabel', () => {
    it('returns correct labels', () => {
      expect(getConfidenceLabel('high')).toBe('High Confidence');
      expect(getConfidenceLabel('medium')).toBe('Medium Confidence');
      expect(getConfidenceLabel('low')).toBe('Low Confidence');
    });
  });

  describe('formatConfidence', () => {
    it('formats score as percentage', () => {
      expect(formatConfidence(0.95)).toBe('95%');
      expect(formatConfidence(0.75)).toBe('75%');
      expect(formatConfidence(1.0)).toBe('100%');
      expect(formatConfidence(0.0)).toBe('0%');
    });

    it('rounds to whole numbers', () => {
      expect(formatConfidence(0.555)).toBe('56%');
      expect(formatConfidence(0.954)).toBe('95%');
    });
  });

  describe('getConfidenceClasses', () => {
    it('returns correct CSS classes for high confidence', () => {
      const classes = getConfidenceClasses('high');
      expect(classes.container).toContain('green');
      expect(classes.badge).toContain('green');
      expect(classes.text).toContain('green');
    });

    it('returns correct CSS classes for medium confidence', () => {
      const classes = getConfidenceClasses('medium');
      expect(classes.container).toContain('amber');
      expect(classes.badge).toContain('amber');
      expect(classes.text).toContain('amber');
    });

    it('returns correct CSS classes for low confidence', () => {
      const classes = getConfidenceClasses('low');
      expect(classes.container).toContain('red');
      expect(classes.badge).toContain('red');
      expect(classes.text).toContain('red');
    });
  });

  describe('constants', () => {
    it('has correct thresholds', () => {
      expect(CONFIDENCE_THRESHOLDS.high).toBe(0.9);
      expect(CONFIDENCE_THRESHOLDS.medium).toBe(0.7);
      expect(CONFIDENCE_THRESHOLDS.low).toBe(0.5);
    });

    it('has colors for all levels', () => {
      expect(CONFIDENCE_COLORS.high).toBeDefined();
      expect(CONFIDENCE_COLORS.medium).toBeDefined();
      expect(CONFIDENCE_COLORS.low).toBeDefined();
    });

    it('has badges for all levels', () => {
      expect(CONFIDENCE_BADGES.high).toBe('🟢');
      expect(CONFIDENCE_BADGES.medium).toBe('🟡');
      expect(CONFIDENCE_BADGES.low).toBe('🔴');
    });
  });
});

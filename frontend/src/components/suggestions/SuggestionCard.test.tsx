import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SuggestionCard } from './SuggestionCard';
import type { Suggestion } from '@/types';

const mockSuggestion: Suggestion = {
  id: 'sug_123',
  entityId: 'ent_abc',
  matchedEntityId: 'ent_xyz',
  matchType: 'exact_string',
  matchValue: 'john.doe@example.com',
  confidence: 0.95,
  confidenceLevel: 'high',
  factors: [
    { name: 'Exact email match', description: 'Email matches exactly', weight: 0.4, score: 1.0 },
    { name: 'Domain verification', description: 'Domain is valid', weight: 0.3, score: 0.95 },
  ],
  status: 'pending',
  createdAt: '2026-01-14T10:00:00Z',
  updatedAt: '2026-01-14T10:00:00Z',
  _links: {
    self: { href: '/api/v1/suggestions/sug_123' },
    entity: { href: '/api/v1/entities/ent_abc' },
    matchedEntity: { href: '/api/v1/entities/ent_xyz' },
  },
};

describe('SuggestionCard', () => {
  it('renders suggestion information correctly', () => {
    render(<SuggestionCard suggestion={mockSuggestion} />);

    expect(screen.getByText('john.doe@example.com')).toBeInTheDocument();
    expect(screen.getByText(/ent_xyz/)).toBeInTheDocument();
    expect(screen.getByText('HIGH CONFIDENCE')).toBeInTheDocument();
    expect(screen.getByText('(95%)')).toBeInTheDocument();
  });

  it('shows action buttons', () => {
    render(<SuggestionCard suggestion={mockSuggestion} />);

    expect(screen.getByText('View Profile')).toBeInTheDocument();
    expect(screen.getByText('Link Entities')).toBeInTheDocument();
    expect(screen.getByText('Merge Duplicates')).toBeInTheDocument();
  });

  it('expands to show match factors when clicked', () => {
    render(<SuggestionCard suggestion={mockSuggestion} />);

    // Factors not visible initially
    expect(screen.queryByText('Match Factors:')).not.toBeInTheDocument();

    // Click expand button
    fireEvent.click(screen.getByText('Why this match?'));

    // Factors visible now
    expect(screen.getByText('Match Factors:')).toBeInTheDocument();
    expect(screen.getByText('Exact email match')).toBeInTheDocument();
    expect(screen.getByText('Domain verification')).toBeInTheDocument();
  });

  it('calls onDismiss with reason when dismissed', () => {
    const onDismiss = vi.fn();
    render(<SuggestionCard suggestion={mockSuggestion} onDismiss={onDismiss} />);

    // Click dismiss button (X)
    fireEvent.click(screen.getByTitle('Dismiss suggestion'));

    // Enter reason
    const input = screen.getByPlaceholderText(/Different person/);
    fireEvent.change(input, { target: { value: 'Not the same person' } });

    // Click dismiss
    fireEvent.click(screen.getByText('Dismiss'));

    expect(onDismiss).toHaveBeenCalledWith(mockSuggestion, 'Not the same person');
  });

  it('requires reason before dismissing', () => {
    const onDismiss = vi.fn();
    render(<SuggestionCard suggestion={mockSuggestion} onDismiss={onDismiss} />);

    // Click dismiss button
    fireEvent.click(screen.getByTitle('Dismiss suggestion'));

    // Dismiss button should be disabled without reason
    const dismissButton = screen.getByRole('button', { name: 'Dismiss' });
    expect(dismissButton).toHaveStyle({ opacity: '0.5' });
  });

  it('calls onLink when Link Entities clicked', () => {
    const onLink = vi.fn();
    render(<SuggestionCard suggestion={mockSuggestion} onLink={onLink} />);

    fireEvent.click(screen.getByText('Link Entities'));

    expect(onLink).toHaveBeenCalledWith(mockSuggestion);
  });

  it('calls onMerge when Merge Duplicates clicked', () => {
    const onMerge = vi.fn();
    render(<SuggestionCard suggestion={mockSuggestion} onMerge={onMerge} />);

    fireEvent.click(screen.getByText('Merge Duplicates'));

    expect(onMerge).toHaveBeenCalledWith(mockSuggestion);
  });

  it('calls onViewProfile when View Profile clicked', () => {
    const onViewProfile = vi.fn();
    render(
      <SuggestionCard suggestion={mockSuggestion} onViewProfile={onViewProfile} />
    );

    fireEvent.click(screen.getByText('View Profile'));

    expect(onViewProfile).toHaveBeenCalledWith(mockSuggestion);
  });

  it('supports controlled expansion state', () => {
    const onExpandChange = vi.fn();
    const { rerender } = render(
      <SuggestionCard
        suggestion={mockSuggestion}
        isExpanded={false}
        onExpandChange={onExpandChange}
      />
    );

    // Factors not visible
    expect(screen.queryByText('Match Factors:')).not.toBeInTheDocument();

    // Click expand
    fireEvent.click(screen.getByText('Why this match?'));
    expect(onExpandChange).toHaveBeenCalledWith(true);

    // Re-render with expanded state
    rerender(
      <SuggestionCard
        suggestion={mockSuggestion}
        isExpanded={true}
        onExpandChange={onExpandChange}
      />
    );

    expect(screen.getByText('Match Factors:')).toBeInTheDocument();
  });

  it('formats match type correctly', () => {
    render(<SuggestionCard suggestion={mockSuggestion} />);

    expect(screen.getByText(/Exact Match/)).toBeInTheDocument();
  });

  it('renders different confidence levels with correct styling', () => {
    const lowConfidenceSuggestion: Suggestion = {
      ...mockSuggestion,
      confidence: 0.55,
      confidenceLevel: 'low',
    };

    render(<SuggestionCard suggestion={lowConfidenceSuggestion} />);

    expect(screen.getByText('LOW CONFIDENCE')).toBeInTheDocument();
    expect(screen.getByText('🔴')).toBeInTheDocument();
  });
});

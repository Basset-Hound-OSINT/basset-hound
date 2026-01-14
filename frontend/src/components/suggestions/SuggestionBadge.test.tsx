import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SuggestionBadge } from './SuggestionBadge';

describe('SuggestionBadge', () => {
  it('renders high confidence badge correctly', () => {
    render(<SuggestionBadge level="high" score={0.95} />);

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('HIGH CONFIDENCE')).toBeInTheDocument();
    expect(screen.getByText('(95%)')).toBeInTheDocument();
    expect(screen.getByText('🟢')).toBeInTheDocument();
  });

  it('renders medium confidence badge correctly', () => {
    render(<SuggestionBadge level="medium" score={0.75} />);

    expect(screen.getByText('MEDIUM CONFIDENCE')).toBeInTheDocument();
    expect(screen.getByText('(75%)')).toBeInTheDocument();
    expect(screen.getByText('🟡')).toBeInTheDocument();
  });

  it('renders low confidence badge correctly', () => {
    render(<SuggestionBadge level="low" score={0.55} />);

    expect(screen.getByText('LOW CONFIDENCE')).toBeInTheDocument();
    expect(screen.getByText('(55%)')).toBeInTheDocument();
    expect(screen.getByText('🔴')).toBeInTheDocument();
  });

  it('hides score when showScore is false', () => {
    render(<SuggestionBadge level="high" score={0.95} showScore={false} />);

    expect(screen.queryByText('(95%)')).not.toBeInTheDocument();
  });

  it('hides icon when showIcon is false', () => {
    render(<SuggestionBadge level="high" score={0.95} showIcon={false} />);

    expect(screen.queryByText('✓')).not.toBeInTheDocument();
  });

  it('renders compact variant without label', () => {
    render(<SuggestionBadge level="high" score={0.95} variant="compact" />);

    expect(screen.queryByText('HIGH CONFIDENCE')).not.toBeInTheDocument();
    expect(screen.getByText('🟢')).toBeInTheDocument();
  });

  it('renders pill variant', () => {
    render(<SuggestionBadge level="high" score={0.95} variant="pill" />);

    expect(screen.getByText('HIGH CONFIDENCE')).toBeInTheDocument();
  });

  it('has correct aria-label for accessibility', () => {
    render(<SuggestionBadge level="high" score={0.95} />);

    expect(screen.getByRole('status')).toHaveAttribute(
      'aria-label',
      'High Confidence: 95%'
    );
  });

  it('applies custom className', () => {
    render(
      <SuggestionBadge level="high" score={0.95} className="custom-class" />
    );

    expect(screen.getByRole('status')).toHaveClass('custom-class');
  });
});

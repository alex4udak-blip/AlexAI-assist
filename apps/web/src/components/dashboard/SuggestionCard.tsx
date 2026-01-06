import { Sparkles, Check, X, ArrowRight } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { Suggestion } from '../../lib/api';

interface SuggestionCardProps {
  suggestion: Suggestion;
  onAccept?: (id: string) => void;
  onDismiss?: (id: string) => void;
}

export function SuggestionCard({
  suggestion,
  onAccept,
  onDismiss,
}: SuggestionCardProps) {
  const impactColors = {
    high: 'success',
    medium: 'warning',
    low: 'default',
  } as const;

  return (
    <Card variant="interactive" className="group">
      <div className="flex items-start gap-4">
        <div className="p-2 bg-accent-muted rounded-lg">
          <Sparkles className="w-5 h-5 text-accent-primary" />
        </div>
        <div className="flex-1">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-sm font-medium text-text-primary">
                {suggestion.title}
              </h3>
              <p className="text-xs text-text-tertiary mt-1">
                {suggestion.description}
              </p>
            </div>
            <Badge variant={impactColors[suggestion.impact as keyof typeof impactColors] || 'default'}>
              {suggestion.impact} impact
            </Badge>
          </div>

          <div className="flex items-center gap-4 mt-4">
            <div className="flex items-center gap-1 text-xs text-text-muted">
              <span>Confidence:</span>
              <span className="text-text-secondary">
                {(suggestion.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex items-center gap-1 text-xs text-text-muted">
              <span>Time saved:</span>
              <span className="text-text-secondary">
                {suggestion.time_saved_minutes}m/day
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              size="sm"
              onClick={() => onAccept?.(suggestion.id)}
            >
              <Check className="w-4 h-4" />
              Accept
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDismiss?.(suggestion.id)}
            >
              <X className="w-4 h-4" />
              Dismiss
            </Button>
            <Button variant="ghost" size="sm" className="ml-auto">
              Learn more
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

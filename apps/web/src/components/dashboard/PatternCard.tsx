import { Layers, TrendingUp, Clock } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { Pattern } from '../../lib/api';

interface PatternCardProps {
  pattern: Pattern;
  onClick?: () => void;
}

export function PatternCard({ pattern, onClick }: PatternCardProps) {
  const complexityColors = {
    low: 'success',
    medium: 'warning',
    high: 'error',
  } as const;

  return (
    <Card
      variant="interactive"
      className="cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start gap-4">
        <div className="p-2 bg-bg-tertiary rounded-lg">
          <Layers className="w-5 h-5 text-text-secondary" />
        </div>
        <div className="flex-1">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-sm font-medium text-text-primary">
                {pattern.name}
              </h3>
              <p className="text-xs text-text-tertiary mt-1">
                {pattern.description}
              </p>
            </div>
            {pattern.automatable && (
              <Badge variant="info">Automatable</Badge>
            )}
          </div>

          <div className="flex items-center gap-4 mt-4">
            <div className="flex items-center gap-1.5 text-xs text-text-muted">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>{pattern.occurrences} occurrences</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-text-muted">
              <Clock className="w-3.5 h-3.5" />
              <span>{pattern.avg_duration_seconds?.toFixed(0) || 0}s avg</span>
            </div>
            <Badge
              variant={complexityColors[pattern.complexity as keyof typeof complexityColors] || 'default'}
              className="ml-auto"
            >
              {pattern.complexity}
            </Badge>
          </div>
        </div>
      </div>
    </Card>
  );
}

import { TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Progress } from '../ui/Progress';
import { cn } from '../../lib/utils';

interface ProductivityScoreProps {
  data?: {
    score: number;
    productive_events: number;
    total_events: number;
    trend: string;
  };
  loading?: boolean;
}

export function ProductivityScore({ data, loading }: ProductivityScoreProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Productivity Score</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 skeleton rounded" />
        </CardContent>
      </Card>
    );
  }

  const score = data?.score ?? 0;
  const trend = data?.trend ?? 'neutral';
  const TrendIcon = trend === 'up' ? TrendingUp : TrendingDown;

  const scoreVariant =
    score >= 70 ? 'success' : score >= 40 ? 'warning' : 'error';

  return (
    <Card>
      <CardHeader>
        <CardTitle>Productivity Score</CardTitle>
        <div
          className={cn(
            'flex items-center gap-1 text-sm',
            trend === 'up' ? 'text-status-success' : 'text-status-error'
          )}
        >
          <TrendIcon className="w-4 h-4" />
          <span>{trend === 'up' ? '+' : '-'}5%</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <div className="relative w-24 h-24">
            <svg className="w-24 h-24 transform -rotate-90">
              <circle
                cx="48"
                cy="48"
                r="40"
                stroke="#27272a"
                strokeWidth="8"
                fill="none"
              />
              <circle
                cx="48"
                cy="48"
                r="40"
                stroke={
                  scoreVariant === 'success'
                    ? '#22c55e'
                    : scoreVariant === 'warning'
                    ? '#eab308'
                    : '#ef4444'
                }
                strokeWidth="8"
                fill="none"
                strokeDasharray={`${(score / 100) * 251.2} 251.2`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-text-primary">
                {score}
              </span>
            </div>
          </div>
          <div className="flex-1 space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-text-secondary">Productive Events</span>
                <span className="text-text-primary">
                  {data?.productive_events ?? 0}
                </span>
              </div>
              <Progress value={data?.productive_events ?? 0} max={data?.total_events ?? 1} size="sm" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-text-secondary">Total Events</span>
                <span className="text-text-primary">
                  {data?.total_events ?? 0}
                </span>
              </div>
              <Progress value={data?.total_events ?? 0} max={data?.total_events ?? 1} size="sm" variant="default" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Progress } from '../ui/Progress';
import { Sparkles } from 'lucide-react';

export interface AIUsage {
  daily_usage: {
    haiku: {
      requests: number;
      cost: number;
    };
    sonnet: {
      requests: number;
      cost: number;
    };
    opus: {
      requests: number;
      cost: number;
    };
  };
  daily_budget: number;
  total_spent_today: number;
}

interface AIUsageCardProps {
  usage: AIUsage | null;
  loading?: boolean;
}

export function AIUsageCard({ usage, loading }: AIUsageCardProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent-primary" />
            <CardTitle>AI Usage Today</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-bg-tertiary rounded w-3/4"></div>
            <div className="h-4 bg-bg-tertiary rounded w-1/2"></div>
            <div className="h-4 bg-bg-tertiary rounded w-2/3"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!usage) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent-primary" />
            <CardTitle>AI Usage Today</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-tertiary">No usage data available</p>
        </CardContent>
      </Card>
    );
  }

  const budgetUsedPercent = (usage.total_spent_today / usage.daily_budget) * 100;
  const budgetRemaining = usage.daily_budget - usage.total_spent_today;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-accent-primary" />
          <CardTitle>AI Usage Today</CardTitle>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Budget Overview */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-text-secondary">Daily Budget</span>
            <span className="text-sm font-medium text-text-primary">
              ${budgetRemaining.toFixed(2)} remaining
            </span>
          </div>
          <Progress
            value={budgetUsedPercent}
            className="h-2"
            variant={
              budgetUsedPercent > 90
                ? 'error'
                : budgetUsedPercent > 75
                ? 'warning'
                : 'default'
            }
          />
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs text-text-tertiary">
              ${usage.total_spent_today.toFixed(2)} spent
            </span>
            <span className="text-xs text-text-tertiary">
              ${usage.daily_budget.toFixed(2)} total
            </span>
          </div>
        </div>

        {/* Model Usage */}
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-text-tertiary uppercase tracking-wider">
            Usage by Model
          </h4>

          {/* Haiku */}
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-text-secondary">Haiku</span>
                <span className="text-xs text-text-tertiary">
                  {usage.daily_usage.haiku.requests} requests
                </span>
              </div>
              <Progress
                value={
                  (usage.daily_usage.haiku.cost / usage.daily_budget) * 100
                }
                className="h-1.5"
              />
            </div>
            <span className="text-sm font-medium text-text-primary ml-4 w-16 text-right">
              ${usage.daily_usage.haiku.cost.toFixed(2)}
            </span>
          </div>

          {/* Sonnet */}
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-text-secondary">Sonnet</span>
                <span className="text-xs text-text-tertiary">
                  {usage.daily_usage.sonnet.requests} requests
                </span>
              </div>
              <Progress
                value={
                  (usage.daily_usage.sonnet.cost / usage.daily_budget) * 100
                }
                className="h-1.5"
              />
            </div>
            <span className="text-sm font-medium text-text-primary ml-4 w-16 text-right">
              ${usage.daily_usage.sonnet.cost.toFixed(2)}
            </span>
          </div>

          {/* Opus */}
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-text-secondary">Opus</span>
                <span className="text-xs text-text-tertiary">
                  {usage.daily_usage.opus.requests} requests
                </span>
              </div>
              <Progress
                value={(usage.daily_usage.opus.cost / usage.daily_budget) * 100}
                className="h-1.5"
              />
            </div>
            <span className="text-sm font-medium text-text-primary ml-4 w-16 text-right">
              ${usage.daily_usage.opus.cost.toFixed(2)}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

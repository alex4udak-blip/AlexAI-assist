import { Activity, Bot, Sparkles, Clock } from 'lucide-react';
import { Card } from '../ui/Card';
import { cn, formatNumber } from '../../lib/utils';

interface Stat {
  label: string;
  value: number | string;
  change?: number;
  icon: typeof Activity;
}

interface StatsGridProps {
  stats?: {
    totalEvents: number;
    activeAgents: number;
    suggestions: number;
    timeSaved: number;
  };
  loading?: boolean;
}

export function StatsGrid({ stats, loading }: StatsGridProps) {
  const items: Stat[] = [
    {
      label: 'Событий сегодня',
      value: stats?.totalEvents ?? 0,
      change: 12,
      icon: Activity,
    },
    {
      label: 'Активных агентов',
      value: stats?.activeAgents ?? 0,
      change: 0,
      icon: Bot,
    },
    {
      label: 'Предложений',
      value: stats?.suggestions ?? 0,
      change: 3,
      icon: Sparkles,
    },
    {
      label: 'Сэкономлено',
      value: stats?.timeSaved ? `${stats.timeSaved}м` : '0м',
      change: 15,
      icon: Clock,
    },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <div className="h-20" />
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {items.map((stat) => (
        <Card key={stat.label}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-text-secondary">{stat.label}</p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {typeof stat.value === 'number'
                  ? formatNumber(stat.value)
                  : stat.value}
              </p>
              {stat.change !== undefined && stat.change !== 0 && (
                <p
                  className={cn(
                    'text-xs mt-1',
                    stat.change > 0 ? 'text-status-success' : 'text-status-error'
                  )}
                >
                  {stat.change > 0 ? '+' : ''}
                  {stat.change}% к вчера
                </p>
              )}
            </div>
            <div className="p-2 bg-accent-muted rounded-lg">
              <stat.icon className="w-5 h-5 text-accent-primary" />
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

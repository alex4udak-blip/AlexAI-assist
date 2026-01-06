import { Monitor, FileText, Globe, Code } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { formatRelativeTime, truncate } from '../../lib/utils';
import type { Event } from '../../lib/api';

interface TimelineProps {
  events?: Event[];
  loading?: boolean;
}

const categoryIcons: Record<string, typeof Monitor> = {
  coding: Code,
  browsing: Globe,
  writing: FileText,
  default: Monitor,
};

export function Timeline({ events, loading }: TimelineProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex gap-3 animate-pulse">
                <div className="w-8 h-8 rounded-lg skeleton" />
                <div className="flex-1">
                  <div className="h-4 w-32 skeleton mb-2" />
                  <div className="h-3 w-48 skeleton" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {events && events.length > 0 ? (
            events.slice(0, 10).map((event) => {
              const Icon =
                categoryIcons[event.category || 'default'] ||
                categoryIcons.default;

              return (
                <div key={event.id} className="flex gap-3 group">
                  <div className="w-8 h-8 rounded-lg bg-bg-tertiary flex items-center justify-center shrink-0">
                    <Icon className="w-4 h-4 text-text-secondary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary">
                      {event.app_name || 'Unknown App'}
                    </p>
                    <p className="text-xs text-text-tertiary truncate">
                      {truncate(event.window_title || '', 50)}
                    </p>
                  </div>
                  <span className="text-xs text-text-muted shrink-0">
                    {formatRelativeTime(event.timestamp)}
                  </span>
                </div>
              );
            })
          ) : (
            <p className="text-sm text-text-muted text-center py-8">
              No recent activity
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

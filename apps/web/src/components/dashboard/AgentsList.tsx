import { Play, Pause, MoreHorizontal } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { Agent } from '../../lib/api';

interface AgentsListProps {
  agents?: Agent[];
  loading?: boolean;
  onRun?: (id: string) => void;
  onToggle?: (id: string, enabled: boolean) => void;
}

export function AgentsList({
  agents,
  loading,
  onRun,
  onToggle,
}: AgentsListProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Active Agents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="p-3 rounded-lg bg-bg-tertiary animate-pulse"
              >
                <div className="h-16" />
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
        <CardTitle>Active Agents</CardTitle>
        <Button variant="ghost" size="sm">
          View All
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {agents && agents.length > 0 ? (
            agents.slice(0, 5).map((agent) => (
              <div
                key={agent.id}
                className="p-3 rounded-lg bg-bg-tertiary hover:bg-bg-hover transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-medium text-text-primary">
                        {agent.name}
                      </h4>
                      <Badge
                        variant={
                          agent.status === 'active' ? 'success' : 'default'
                        }
                      >
                        {agent.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-text-tertiary mt-1">
                      {agent.run_count} runs | {agent.success_count} successful
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    {agent.status === 'active' ? (
                      <button
                        onClick={() => onToggle?.(agent.id, false)}
                        className="p-1.5 text-text-secondary hover:text-status-warning hover:bg-bg-hover rounded-lg transition-colors"
                        title="Pause agent"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        onClick={() => onToggle?.(agent.id, true)}
                        className="p-1.5 text-text-secondary hover:text-status-success hover:bg-bg-hover rounded-lg transition-colors"
                        title="Enable agent"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => onRun?.(agent.id)}
                      className="p-1.5 text-text-secondary hover:text-accent-primary hover:bg-bg-hover rounded-lg transition-colors"
                      title="Run now"
                    >
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-text-muted text-center py-8">
              No agents configured
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

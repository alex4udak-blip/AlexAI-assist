import { Play, Pause, Settings, Trash2, MoreVertical } from 'lucide-react';
import { useState } from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { formatRelativeTime, formatDuration } from '../../lib/utils';
import type { Agent } from '../../lib/api';

interface AgentCardProps {
  agent: Agent;
  onRun?: (id: string) => void;
  onEnable?: (id: string) => void;
  onDisable?: (id: string) => void;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}

export function AgentCard({
  agent,
  onRun,
  onEnable,
  onDisable,
  onEdit,
  onDelete,
}: AgentCardProps) {
  const [showMenu, setShowMenu] = useState(false);

  const statusVariants = {
    active: 'success',
    disabled: 'error',
    draft: 'warning',
  } as const;

  return (
    <Card className="relative">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-text-primary">
              {agent.name}
            </h3>
            <Badge variant={statusVariants[agent.status as keyof typeof statusVariants] || 'default'}>
              {agent.status}
            </Badge>
          </div>
          <p className="text-sm text-text-tertiary mt-1">{agent.description}</p>
        </div>
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-2 text-text-secondary hover:text-text-primary hover:bg-bg-hover rounded-lg transition-colors"
          >
            <MoreVertical className="w-5 h-5" />
          </button>
          {showMenu && (
            <div className="absolute right-0 top-10 w-48 bg-bg-elevated border border-border-default rounded-lg shadow-lg py-1 z-10">
              <button
                onClick={() => {
                  onEdit?.(agent.id);
                  setShowMenu(false);
                }}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-bg-hover"
              >
                <Settings className="w-4 h-4" />
                Edit
              </button>
              <button
                onClick={() => {
                  onDelete?.(agent.id);
                  setShowMenu(false);
                }}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-status-error hover:bg-status-error/10"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <p className="text-xs text-text-muted">Total Runs</p>
          <p className="text-lg font-semibold text-text-primary">
            {agent.run_count}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Success Rate</p>
          <p className="text-lg font-semibold text-text-primary">
            {agent.run_count > 0
              ? ((agent.success_count / agent.run_count) * 100).toFixed(0)
              : 0}
            %
          </p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Time Saved</p>
          <p className="text-lg font-semibold text-text-primary">
            {formatDuration(agent.total_time_saved_seconds)}
          </p>
        </div>
      </div>

      {agent.last_run_at && (
        <p className="text-xs text-text-muted mb-4">
          Last run: {formatRelativeTime(agent.last_run_at)}
        </p>
      )}

      <div className="flex items-center gap-2">
        <Button size="sm" onClick={() => onRun?.(agent.id)}>
          <Play className="w-4 h-4" />
          Run Now
        </Button>
        {agent.status === 'active' ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onDisable?.(agent.id)}
          >
            <Pause className="w-4 h-4" />
            Disable
          </Button>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onEnable?.(agent.id)}
          >
            <Play className="w-4 h-4" />
            Enable
          </Button>
        )}
      </div>
    </Card>
  );
}

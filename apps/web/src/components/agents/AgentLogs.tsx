import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { useAgentLogs } from '../../hooks/useAgents';
import { formatDateTime, cn } from '../../lib/utils';

interface AgentLogsProps {
  agentId: string;
}

const levelIcons = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: AlertCircle,
};

const levelColors = {
  info: 'text-status-info',
  success: 'text-status-success',
  warning: 'text-status-warning',
  error: 'text-status-error',
};

export function AgentLogs({ agentId }: AgentLogsProps) {
  const { data: logs, loading } = useAgentLogs(agentId);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Logs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 skeleton rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Logs</CardTitle>
      </CardHeader>
      <CardContent>
        {logs && logs.length > 0 ? (
          <div className="space-y-2">
            {logs.map((log) => {
              const Icon =
                levelIcons[log.level as keyof typeof levelIcons] || Info;
              const color =
                levelColors[log.level as keyof typeof levelColors] ||
                'text-text-secondary';

              return (
                <div
                  key={log.id}
                  className="flex items-start gap-3 p-3 bg-bg-tertiary rounded-lg"
                >
                  <Icon className={cn('w-4 h-4 mt-0.5 shrink-0', color)} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-primary">{log.message}</p>
                    {log.data && (
                      <pre className="mt-2 text-xs text-text-tertiary bg-bg-primary p-2 rounded overflow-auto">
                        {JSON.stringify(log.data, null, 2)}
                      </pre>
                    )}
                  </div>
                  <span className="text-xs text-text-muted shrink-0">
                    {formatDateTime(log.created_at)}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-text-muted text-center py-8">No logs yet</p>
        )}
      </CardContent>
    </Card>
  );
}

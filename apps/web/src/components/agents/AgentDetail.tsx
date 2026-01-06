import { useState } from 'react';
import { ArrowLeft, Play, Settings, Code } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Tabs, TabPanel } from '../ui/Tabs';
import { AgentLogs } from './AgentLogs';
import { formatDateTime, formatDuration } from '../../lib/utils';
import type { Agent } from '../../lib/api';

interface AgentDetailProps {
  agent: Agent;
  onBack: () => void;
  onRun?: (id: string) => void;
  onEdit?: (id: string) => void;
}

export function AgentDetail({ agent, onBack, onRun, onEdit }: AgentDetailProps) {
  const [activeTab, setActiveTab] = useState('overview');

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'logs', label: 'Logs' },
    { id: 'code', label: 'Code', icon: <Code className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 text-text-secondary hover:text-text-primary hover:bg-bg-hover rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-text-primary">{agent.name}</h1>
            <Badge
              variant={
                agent.status === 'active'
                  ? 'success'
                  : agent.status === 'disabled'
                  ? 'error'
                  : 'warning'
              }
            >
              {agent.status}
            </Badge>
          </div>
          <p className="text-text-tertiary mt-1">{agent.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => onEdit?.(agent.id)}>
            <Settings className="w-4 h-4" />
            Edit
          </Button>
          <Button onClick={() => onRun?.(agent.id)}>
            <Play className="w-4 h-4" />
            Run Now
          </Button>
        </div>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      <TabPanel id="overview" activeTab={activeTab}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-text-muted">Total Runs</p>
                  <p className="text-2xl font-bold text-text-primary">
                    {agent.run_count}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-text-muted">Success Rate</p>
                  <p className="text-2xl font-bold text-status-success">
                    {agent.run_count > 0
                      ? ((agent.success_count / agent.run_count) * 100).toFixed(0)
                      : 0}
                    %
                  </p>
                </div>
                <div>
                  <p className="text-sm text-text-muted">Time Saved</p>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatDuration(agent.total_time_saved_seconds)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-text-muted">Errors</p>
                  <p className="text-2xl font-bold text-status-error">
                    {agent.error_count}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-text-muted">Type</dt>
                  <dd className="text-text-primary">{agent.agent_type}</dd>
                </div>
                <div>
                  <dt className="text-sm text-text-muted">Created</dt>
                  <dd className="text-text-primary">
                    {formatDateTime(agent.created_at)}
                  </dd>
                </div>
                {agent.last_run_at && (
                  <div>
                    <dt className="text-sm text-text-muted">Last Run</dt>
                    <dd className="text-text-primary">
                      {formatDateTime(agent.last_run_at)}
                    </dd>
                  </div>
                )}
                {agent.last_error && (
                  <div>
                    <dt className="text-sm text-text-muted">Last Error</dt>
                    <dd className="text-status-error text-sm">
                      {agent.last_error}
                    </dd>
                  </div>
                )}
              </dl>
            </CardContent>
          </Card>
        </div>
      </TabPanel>

      <TabPanel id="logs" activeTab={activeTab}>
        <AgentLogs agentId={agent.id} />
      </TabPanel>

      <TabPanel id="code" activeTab={activeTab}>
        <Card>
          <CardHeader>
            <CardTitle>Agent Code</CardTitle>
          </CardHeader>
          <CardContent>
            {agent.code ? (
              <pre className="bg-bg-tertiary p-4 rounded-lg overflow-auto text-sm font-mono text-text-secondary">
                {agent.code}
              </pre>
            ) : (
              <p className="text-text-muted text-center py-8">
                No custom code defined
              </p>
            )}
          </CardContent>
        </Card>
      </TabPanel>
    </div>
  );
}

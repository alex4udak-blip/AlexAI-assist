import { StatsGrid } from '../components/dashboard/StatsGrid';
import { ActivityChart } from '../components/dashboard/ActivityChart';
import { Timeline } from '../components/dashboard/Timeline';
import { AgentsList } from '../components/dashboard/AgentsList';
import { SuggestionCard } from '../components/dashboard/SuggestionCard';
import { useAnalyticsSummary, useTimeline } from '../hooks/useAnalytics';
import { useAgents } from '../hooks/useAgents';
import { useSuggestions } from '../hooks/usePatterns';
import { useMutation } from '../hooks/useApi';
import { api } from '../lib/api';

export default function Dashboard() {
  const { data: summary, loading: summaryLoading } = useAnalyticsSummary();
  const { data: timeline, loading: timelineLoading } = useTimeline(24);
  const { data: agents, loading: agentsLoading, refetch: refetchAgents } = useAgents({ status: 'active' });
  const { data: suggestions, loading: suggestionsLoading, refetch: refetchSuggestions } = useSuggestions({ status: 'pending' });

  const { mutate: acceptSuggestion } = useMutation(api.acceptSuggestion);
  const { mutate: dismissSuggestion } = useMutation(api.dismissSuggestion);
  const { mutate: runAgent } = useMutation(api.runAgent);
  const { mutate: enableAgent } = useMutation(api.enableAgent);
  const { mutate: disableAgent } = useMutation(api.disableAgent);

  const handleAcceptSuggestion = async (id: string) => {
    await acceptSuggestion(id);
    refetchSuggestions();
    refetchAgents();
  };

  const handleDismissSuggestion = async (id: string) => {
    await dismissSuggestion(id);
    refetchSuggestions();
  };

  const handleRunAgent = async (id: string) => {
    await runAgent(id);
    refetchAgents();
  };

  const handleToggleAgent = async (id: string, enabled: boolean) => {
    if (enabled) {
      await enableAgent(id);
    } else {
      await disableAgent(id);
    }
    refetchAgents();
  };

  // Transform hourly activity data for chart
  const hourlyData = summary?.hourly_activity
    ? Object.entries(summary.hourly_activity).map(([hour, count]) => ({
        hour: parseInt(hour),
        count: count as number,
      }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
        <p className="text-text-tertiary mt-1">
          Overview of your activity and automations
        </p>
      </div>

      <StatsGrid
        stats={{
          totalEvents: summary?.total_events ?? 0,
          activeAgents: agents?.length ?? 0,
          suggestions: suggestions?.length ?? 0,
          timeSaved: 0,
        }}
        loading={summaryLoading}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ActivityChart data={hourlyData} loading={summaryLoading} />
        </div>
        <div>
          <Timeline events={timeline ?? undefined} loading={timelineLoading} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AgentsList
          agents={agents ?? undefined}
          loading={agentsLoading}
          onRun={handleRunAgent}
          onToggle={handleToggleAgent}
        />
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-text-primary">
            Suggestions
          </h2>
          {suggestionsLoading ? (
            <div className="space-y-4">
              {[...Array(2)].map((_, i) => (
                <div key={i} className="h-32 skeleton rounded-xl" />
              ))}
            </div>
          ) : suggestions && suggestions.length > 0 ? (
            suggestions.slice(0, 3).map((suggestion) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                onAccept={handleAcceptSuggestion}
                onDismiss={handleDismissSuggestion}
              />
            ))
          ) : (
            <div className="bg-bg-secondary border border-border-subtle rounded-xl p-8 text-center">
              <p className="text-text-muted">No suggestions yet</p>
              <p className="text-xs text-text-tertiary mt-1">
                Keep using your device to generate patterns
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

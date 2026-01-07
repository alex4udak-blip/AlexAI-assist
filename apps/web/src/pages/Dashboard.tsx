import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
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

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

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
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6 max-w-7xl mx-auto"
    >
      {/* Stats */}
      <motion.div variants={item}>
        <StatsGrid
          stats={{
            totalEvents: summary?.total_events ?? 0,
            activeAgents: agents?.length ?? 0,
            suggestions: suggestions?.length ?? 0,
            timeSaved: 0,
          }}
          loading={summaryLoading}
        />
      </motion.div>

      {/* Chart + Timeline */}
      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ActivityChart data={hourlyData} loading={summaryLoading} />
        </div>
        <div className="min-h-[400px]">
          <Timeline events={timeline ?? undefined} loading={timelineLoading} />
        </div>
      </motion.div>

      {/* Agents + Suggestions */}
      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AgentsList
          agents={agents ?? undefined}
          loading={agentsLoading}
          onRun={handleRunAgent}
          onToggle={handleToggleAgent}
        />

        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-text-primary tracking-tight">
            Предложения
          </h2>

          {suggestionsLoading ? (
            <div className="space-y-3">
              {[...Array(2)].map((_, i) => (
                <div key={i} className="p-4 rounded-xl border border-border-subtle bg-surface-primary">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl skeleton" />
                    <div className="flex-1">
                      <div className="h-5 w-40 skeleton mb-2" />
                      <div className="h-4 w-full skeleton mb-3" />
                      <div className="h-8 w-32 skeleton" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : suggestions && suggestions.length > 0 ? (
            <div className="space-y-3">
              {suggestions.slice(0, 3).map((suggestion) => (
                <SuggestionCard
                  key={suggestion.id}
                  suggestion={suggestion}
                  onAccept={handleAcceptSuggestion}
                  onDismiss={handleDismissSuggestion}
                />
              ))}
            </div>
          ) : (
            <div className="p-8 rounded-2xl border border-border-subtle bg-surface-primary text-center">
              <Sparkles className="w-10 h-10 text-text-muted mx-auto mb-3" />
              <p className="text-text-tertiary text-sm">Пока нет предложений</p>
              <p className="text-xs text-text-muted mt-1">
                Продолжайте использовать устройство для выявления паттернов
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

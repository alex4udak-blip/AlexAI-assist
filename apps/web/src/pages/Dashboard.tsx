import { motion } from 'framer-motion';
import { useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  // Desktop components
  StatusBar,
  ActivityRings,
  WeeklyHeatmap,
  CurrentFocus,
  AgentGrid,
  AgentActivityStream,
  AIInsights,
  Achievements,
  QuickActions,
  LiveTimeline,
  // Mobile components
  MobileHeader,
  AgentCarousel,
  CompactHeatmap,
  UnifiedFeed,
  MobileAchievements,
} from '../components/hud';
import { Plus } from 'lucide-react';
import { useAnalyticsSummary, useTimeline, useProductivity } from '../hooks/useAnalytics';
import { useAgents } from '../hooks/useAgents';
import { useSuggestions } from '../hooks/usePatterns';
import { useMutation } from '../hooks/useApi';
import { api } from '../lib/api';
import { useIsMobile, useIsTablet } from '../hooks/useMediaQuery';
import { useEventsCreated } from '../hooks/useWebSocketSync';
import { useWebSocket } from '../hooks/useWebSocket';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

// Mobile-optimized animation variants
const mobileContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.03 },
  },
};

const mobileItem = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const isTablet = useIsTablet();

  // Connect to WebSocket for real-time updates
  const { isConnected } = useWebSocket();

  const { data: summary } = useAnalyticsSummary();
  const { data: productivity } = useProductivity();
  const { data: timeline, refetch: refetchTimeline } = useTimeline(24);
  const { data: agents, refetch: refetchAgents } = useAgents();
  const { data: suggestions } = useSuggestions({ status: 'pending' });

  // Handle real-time event updates
  const handleEventsCreated = useCallback(() => {
    // Refetch timeline and analytics when new events arrive
    refetchTimeline();
  }, [refetchTimeline]);

  // Subscribe to real-time events
  useEventsCreated(handleEventsCreated);

  const { mutate: runAgent } = useMutation(api.runAgent);
  const { mutate: enableAgent } = useMutation(api.enableAgent);
  const { mutate: disableAgent } = useMutation(api.disableAgent);

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

  const handleCreateAgent = () => {
    navigate('/agents');
  };

  const handleRefresh = async () => {
    await Promise.all([refetchAgents(), refetchTimeline()]);
  };

  // Calculate activity rings data
  const ringsData = useMemo(() => ({
    productivity: productivity?.score ?? 0,
    focus: Math.min(100, (summary?.total_events ?? 0) / 5),
    automation: agents?.filter(a => a.status === 'active').length
      ? Math.min(100, agents.reduce((acc, a) => acc + a.total_time_saved_seconds, 0) / 36)
      : 0,
  }), [productivity, summary, agents]);

  // Generate weekly heatmap data from timeline
  const heatmapData = useMemo(() => {
    if (!timeline) return [];
    const data: { day: number; hour: number; value: number }[] = [];
    const counts: Record<string, number> = {};

    timeline.forEach(event => {
      const date = new Date(event.timestamp);
      const day = (date.getDay() + 6) % 7;
      const hour = date.getHours();
      const key = `${day}-${hour}`;
      counts[key] = (counts[key] || 0) + 1;
    });

    const maxCount = Math.max(...Object.values(counts), 1);
    Object.entries(counts).forEach(([key, count]) => {
      const [day, hour] = key.split('-').map(Number);
      data.push({ day, hour, value: Math.round((count / maxCount) * 100) });
    });

    return data;
  }, [timeline]);

  // Current focus from latest timeline event
  const currentFocus = useMemo(() => {
    if (!timeline || timeline.length === 0) return null;
    const latest = timeline[0];
    const startTime = new Date(latest.timestamp);
    const now = new Date();
    const minutes = Math.round((now.getTime() - startTime.getTime()) / 60000);
    return {
      appName: latest.app_name || 'Unknown',
      sessionMinutes: Math.min(minutes, 120),
      category: latest.category ?? undefined,
    };
  }, [timeline]);

  // Generate AI insights from data
  const insights = useMemo(() => {
    const result: { id: string; type: 'positive' | 'negative' | 'neutral' | 'suggestion'; message: string; metric?: string }[] = [];

    if (summary && summary.total_events > 0) {
      const topApp = summary.top_apps?.[0];
      if (topApp) {
        result.push({
          id: '1',
          type: 'neutral',
          message: `Сегодня больше всего времени в ${topApp[0]}`,
          metric: `${topApp[1]} событий`,
        });
      }

      if (productivity && productivity.score >= 70) {
        result.push({
          id: '2',
          type: 'positive',
          message: 'Высокая продуктивность сегодня!',
          metric: `${productivity.score}%`,
        });
      }
    }

    if (suggestions && suggestions.length > 0) {
      result.push({
        id: '3',
        type: 'suggestion',
        message: `Найдено ${suggestions.length} паттернов для автоматизации`,
      });
    }

    const activeAgents = agents?.filter(a => a.status === 'active') || [];
    if (activeAgents.length > 0) {
      const totalSaved = activeAgents.reduce((acc, a) => acc + a.total_time_saved_seconds, 0);
      if (totalSaved > 60) {
        result.push({
          id: '4',
          type: 'positive',
          message: 'Агенты экономят ваше время',
          metric: `${Math.round(totalSaved / 60)}м сэкономлено`,
        });
      }
    }

    return result;
  }, [summary, productivity, suggestions, agents]);

  // Calculate activity streak (consecutive days with activity)
  const activityStreak = useMemo(() => {
    if (!timeline || timeline.length === 0) return 0;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Get unique days with activity
    const daysWithActivity = new Set<string>();
    timeline.forEach(event => {
      const date = new Date(event.timestamp);
      date.setHours(0, 0, 0, 0);
      daysWithActivity.add(date.toISOString());
    });

    // Count consecutive days from today backwards
    let streak = 0;
    let checkDate = new Date(today);

    while (true) {
      if (daysWithActivity.has(checkDate.toISOString())) {
        streak++;
        checkDate.setDate(checkDate.getDate() - 1);
      } else {
        break;
      }
    }

    return streak;
  }, [timeline]);

  // Generate achievements
  const achievements = useMemo(() => {
    const result: {
      id: string;
      title: string;
      description: string;
      icon: 'trophy' | 'flame' | 'zap' | 'clock' | 'bot' | 'target';
      progress: number;
      completed: boolean;
      value?: string;
    }[] = [];

    const agentCount = agents?.length ?? 0;
    result.push({
      id: '1',
      title: 'Создатель агентов',
      description: 'Создайте 10 агентов',
      icon: 'bot',
      progress: Math.min(100, (agentCount / 10) * 100),
      completed: agentCount >= 10,
      value: `${agentCount}/10`,
    });

    const totalEvents = summary?.total_events ?? 0;
    result.push({
      id: '2',
      title: 'Активный пользователь',
      description: '1000 событий за день',
      icon: 'target',
      progress: Math.min(100, (totalEvents / 1000) * 100),
      completed: totalEvents >= 1000,
      value: `${totalEvents}/1000`,
    });

    const savedTime = agents?.reduce((acc, a) => acc + a.total_time_saved_seconds, 0) ?? 0;
    const savedHours = savedTime / 3600;
    result.push({
      id: '3',
      title: 'Мастер автоматизации',
      description: 'Сэкономьте 5 часов с агентами',
      icon: 'clock',
      progress: Math.min(100, (savedHours / 5) * 100),
      completed: savedHours >= 5,
      value: `${savedHours.toFixed(1)}/5ч`,
    });

    return result;
  }, [agents, summary]);

  // Calculate system health based on recent events
  const { systemHealth, lastEventMinutesAgo } = useMemo(() => {
    if (!timeline || timeline.length === 0) {
      return { systemHealth: 'warning' as const, lastEventMinutesAgo: 999 };
    }

    const latestEvent = new Date(timeline[0].timestamp);
    const now = new Date();
    const minutesAgo = Math.round((now.getTime() - latestEvent.getTime()) / 60000);

    if (minutesAgo < 5) return { systemHealth: 'healthy' as const, lastEventMinutesAgo: minutesAgo };
    if (minutesAgo < 30) return { systemHealth: 'warning' as const, lastEventMinutesAgo: minutesAgo };
    return { systemHealth: 'critical' as const, lastEventMinutesAgo: minutesAgo };
  }, [timeline]);

  // Generate agent activity stream
  const agentActivities = useMemo(() => {
    if (!agents) return [];
    return agents
      .filter(a => a.last_run_at)
      .map(agent => ({
        id: agent.id,
        agentName: agent.name,
        action: agent.last_error ? `Ошибка: ${agent.last_error}` : 'Выполнен успешно',
        status: agent.last_error ? 'error' as const : 'success' as const,
        timestamp: agent.last_run_at!,
        details: `${agent.run_count} запусков всего`,
      }))
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [agents]);

  // Generate timeline events
  const timelineEvents = useMemo(() => {
    if (!timeline) return [];
    return timeline.slice(0, 50).map(event => ({
      id: event.id,
      type: 'app' as const,
      name: event.app_name || 'Unknown',
      startTime: event.timestamp,
      category: event.category ?? undefined,
    }));
  }, [timeline]);

  // Generate unified feed for mobile
  const unifiedFeedItems = useMemo(() => {
    const items: {
      id: string;
      type: 'agent' | 'activity' | 'insight';
      title: string;
      description: string;
      timestamp: string;
      status?: 'success' | 'error' | 'warning' | 'info';
      icon?: 'bot' | 'monitor' | 'lightbulb' | 'trending-up' | 'trending-down' | 'sparkles';
    }[] = [];

    // Add agent activities
    agentActivities.forEach(activity => {
      items.push({
        id: `agent-${activity.id}`,
        type: 'agent',
        title: activity.agentName,
        description: activity.action,
        timestamp: activity.timestamp,
        status: activity.status,
        icon: 'bot',
      });
    });

    // Add timeline events (last 10)
    timeline?.slice(0, 10).forEach(event => {
      items.push({
        id: `activity-${event.id}`,
        type: 'activity',
        title: event.app_name || 'Unknown',
        description: event.window_title || 'Активность',
        timestamp: event.timestamp,
        status: 'info',
        icon: 'monitor',
      });
    });

    // Add insights
    insights.forEach(insight => {
      items.push({
        id: `insight-${insight.id}`,
        type: 'insight',
        title: insight.type === 'positive' ? 'Хорошие новости' :
               insight.type === 'suggestion' ? 'Рекомендация' : 'Наблюдение',
        description: insight.message,
        timestamp: new Date().toISOString(),
        status: insight.type === 'positive' ? 'success' :
                insight.type === 'negative' ? 'warning' : 'info',
        icon: insight.type === 'suggestion' ? 'sparkles' :
              insight.type === 'positive' ? 'trending-up' : 'lightbulb',
      });
    });

    // Sort by timestamp
    return items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [agentActivities, timeline, insights]);

  const activeAgents = agents?.filter(a => a.status === 'active') || [];

  // Mobile Layout
  if (isMobile) {
    return (
      <>
        <motion.div
          variants={mobileContainer}
          initial="hidden"
          animate="show"
          className="pb-24"
        >
          {/* Mobile Header */}
          <MobileHeader
            productivity={ringsData.productivity}
            focus={ringsData.focus}
            automation={ringsData.automation}
            focusTime={currentFocus?.sessionMinutes}
            currentApp={currentFocus?.appName}
            category={currentFocus?.category}
          />

          {/* Agent Carousel */}
          <motion.div variants={mobileItem} className="mt-4">
            <div className="px-4 mb-3">
              <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono">
                Агенты
              </h3>
            </div>
            <AgentCarousel
              agents={agents ?? []}
              onRunAgent={handleRunAgent}
              onToggleAgent={handleToggleAgent}
              onViewDetails={(id) => navigate(`/agents/${id}`)}
            />
          </motion.div>

          {/* Achievements (horizontal scroll) */}
          <motion.div variants={mobileItem}>
            <MobileAchievements achievements={achievements} streak={activityStreak} />
          </motion.div>

          {/* Compact Heatmap */}
          <motion.div variants={mobileItem} className="px-4 mt-4">
            <CompactHeatmap data={heatmapData} />
          </motion.div>

          {/* Unified Feed */}
          <motion.div variants={mobileItem} className="mt-4 h-[400px]">
            <UnifiedFeed
              items={unifiedFeedItems}
              onRefresh={handleRefresh}
            />
          </motion.div>
        </motion.div>

        {/* FAB Button for creating agent */}
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          whileTap={{ scale: 0.9 }}
          onClick={handleCreateAgent}
          className="fixed right-4 bottom-20 z-50 w-14 h-14 rounded-full
                     bg-hud-gradient shadow-hud flex items-center justify-center
                     active:shadow-hud-lg transition-shadow touch-manipulation"
          style={{ marginBottom: 'env(safe-area-inset-bottom, 0px)' }}
        >
          <Plus className="w-6 h-6 text-white" />
        </motion.button>
      </>
    );
  }

  // Tablet Layout
  if (isTablet) {
    return (
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="space-y-4 max-w-[1200px] mx-auto px-4"
      >
        {/* Status Bar */}
        <motion.div variants={item}>
          <StatusBar
            focusTime={currentFocus?.sessionMinutes}
            activeAgents={activeAgents.length}
            totalAgents={agents?.length ?? 0}
            systemHealth={systemHealth}
            lastEventMinutesAgo={lastEventMinutesAgo}
          />
        </motion.div>

        {/* Two Column Grid for Tablet */}
        <div className="grid grid-cols-2 gap-4">
          {/* Left Column */}
          <div className="space-y-4">
            <motion.div variants={item}>
              <ActivityRings
                productivity={ringsData.productivity}
                focus={ringsData.focus}
                automation={ringsData.automation}
              />
            </motion.div>

            <motion.div variants={item}>
              <CurrentFocus
                appName={currentFocus?.appName}
                sessionMinutes={currentFocus?.sessionMinutes}
                category={currentFocus?.category}
              />
            </motion.div>

            <motion.div variants={item}>
              <AIInsights insights={insights} />
            </motion.div>
          </div>

          {/* Right Column */}
          <div className="space-y-4">
            <motion.div variants={item}>
              <div className="p-5 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                             shadow-inner-glow">
                <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono mb-4">
                  Agent Command Center
                </h3>
                <AgentGrid
                  agents={agents?.slice(0, 4) ?? []}
                  onRunAgent={handleRunAgent}
                  onToggleAgent={handleToggleAgent}
                />
              </div>
            </motion.div>

            <motion.div variants={item}>
              <Achievements achievements={achievements} streak={activityStreak} />
            </motion.div>
          </div>
        </div>

        {/* Full Width Bottom Section */}
        <motion.div variants={item}>
          <WeeklyHeatmap data={heatmapData} />
        </motion.div>

        <motion.div variants={item} className="h-[250px]">
          <AgentActivityStream activities={agentActivities} />
        </motion.div>

        <motion.div variants={item}>
          <QuickActions onCreateAgent={handleCreateAgent} />
        </motion.div>
      </motion.div>
    );
  }

  // Desktop Layout (Original)
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-4 max-w-[1600px] mx-auto"
    >
      {/* Status Bar */}
      <motion.div variants={item}>
        <StatusBar
          focusTime={currentFocus?.sessionMinutes}
          activeAgents={activeAgents.length}
          totalAgents={agents?.length ?? 0}
          systemHealth={systemHealth}
          lastEventMinutesAgo={lastEventMinutesAgo}
        />
      </motion.div>

      {/* Main Bento Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left Column - YOU */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <motion.div variants={item}>
            <ActivityRings
              productivity={ringsData.productivity}
              focus={ringsData.focus}
              automation={ringsData.automation}
            />
          </motion.div>

          <motion.div variants={item}>
            <CurrentFocus
              appName={currentFocus?.appName}
              sessionMinutes={currentFocus?.sessionMinutes}
              category={currentFocus?.category}
            />
          </motion.div>

          <motion.div variants={item}>
            <WeeklyHeatmap data={heatmapData} />
          </motion.div>
        </div>

        {/* Center Column - AGENTS */}
        <div className="col-span-12 lg:col-span-6 space-y-4">
          <motion.div variants={item}>
            <div className="p-5 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                           shadow-inner-glow">
              <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono mb-4">
                Agent Command Center
              </h3>
              <AgentGrid
                agents={agents?.slice(0, 4) ?? []}
                onRunAgent={handleRunAgent}
                onToggleAgent={handleToggleAgent}
              />
            </div>
          </motion.div>

          <motion.div variants={item} className="h-[300px]">
            <AgentActivityStream activities={agentActivities} />
          </motion.div>
        </div>

        {/* Right Column - INSIGHTS & GAMIFICATION */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <motion.div variants={item}>
            <AIInsights insights={insights} />
          </motion.div>

          <motion.div variants={item}>
            <Achievements achievements={achievements} streak={activityStreak} />
          </motion.div>

          <motion.div variants={item}>
            <QuickActions onCreateAgent={handleCreateAgent} />
          </motion.div>
        </div>
      </div>

      {/* Bottom - Timeline */}
      <motion.div variants={item}>
        <LiveTimeline events={timelineEvents} />
      </motion.div>
    </motion.div>
  );
}

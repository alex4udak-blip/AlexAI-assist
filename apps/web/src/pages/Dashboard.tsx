import { motion, AnimatePresence } from 'framer-motion';
import { useMemo, useCallback, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  Bot,
  Clock,
  Command,
  TrendingUp,
  Zap,
  ChevronRight,
  Play,
  Pause,
  CheckCircle2,
  Sparkles,
  Monitor,
  Search,
  Plus,
  Settings,
  MessageSquare,
  BarChart3,
  Calendar,
  Cpu,
  Wifi,
  WifiOff,
  DollarSign,
} from 'lucide-react';
import { useAnalyticsSummary, useTimeline, useProductivity, useCategories, useAppUsage, useAIUsage } from '../hooks/useAnalytics';
import { useAgents } from '../hooks/useAgents';
import { useSuggestions } from '../hooks/usePatterns';
import { useMutation } from '../hooks/useApi';
import { api } from '../lib/api';
import { useEventsCreated } from '../hooks/useWebSocketSync';
import { useWebSocket } from '../hooks/useWebSocket';

// Animation variants
const fadeIn = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

const stagger = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

// Metric Card Component
function MetricCard({
  label,
  value,
  subValue,
  icon: Icon,
  trend,
  accentColor = 'cyan',
}: {
  label: string;
  value: string | number;
  subValue?: string;
  icon: React.ElementType;
  trend?: 'up' | 'down' | 'neutral';
  accentColor?: 'cyan' | 'green' | 'purple' | 'orange';
}) {
  const colors = {
    cyan: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
    green: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
    purple: 'text-violet-400 bg-violet-400/10 border-violet-400/20',
    orange: 'text-orange-400 bg-orange-400/10 border-orange-400/20',
  };

  return (
    <motion.div
      variants={fadeIn}
      className="relative group"
    >
      <div className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800
                      hover:border-zinc-700 transition-all duration-200
                      hover:bg-zinc-900/80">
        <div className="flex items-start justify-between mb-3">
          <div className={`p-2 rounded-lg ${colors[accentColor]}`}>
            <Icon className="w-4 h-4" />
          </div>
          {trend && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              trend === 'up' ? 'text-emerald-400 bg-emerald-400/10' :
              trend === 'down' ? 'text-red-400 bg-red-400/10' :
              'text-zinc-400 bg-zinc-400/10'
            }`}>
              {trend === 'up' ? '+12%' : trend === 'down' ? '-5%' : '0%'}
            </span>
          )}
        </div>
        <div className="space-y-1">
          <div className="text-2xl font-semibold text-white tracking-tight">
            {value}
          </div>
          <div className="text-xs text-zinc-500 uppercase tracking-wider">
            {label}
          </div>
          {subValue && (
            <div className="text-xs text-zinc-400 mt-1">
              {subValue}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// Agent Card Component
function AgentCard({
  agent,
  onRun,
  onToggle,
  onClick,
}: {
  agent: {
    id: string;
    name: string;
    status: string;
    run_count: number;
    success_count: number;
    last_run_at: string | null;
    total_time_saved_seconds: number;
  };
  onRun: () => void;
  onToggle: () => void;
  onClick: () => void;
}) {
  const isActive = agent.status === 'active';
  const successRate = agent.run_count > 0
    ? Math.round((agent.success_count / agent.run_count) * 100)
    : 0;

  return (
    <motion.div
      variants={fadeIn}
      className="group relative"
    >
      <div
        onClick={onClick}
        className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800
                   hover:border-zinc-700 transition-all duration-200 cursor-pointer
                   hover:bg-zinc-900/80"
      >
        <div className="flex items-start justify-between mb-3">
          <div className={`p-2 rounded-lg ${
            isActive ? 'bg-emerald-400/10 text-emerald-400' : 'bg-zinc-800 text-zinc-500'
          }`}>
            <Bot className="w-4 h-4" />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); onRun(); }}
              className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700
                         text-zinc-400 hover:text-white transition-colors"
              title="Run agent"
            >
              <Play className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onToggle(); }}
              className={`p-1.5 rounded-lg transition-colors ${
                isActive
                  ? 'bg-emerald-400/10 text-emerald-400 hover:bg-emerald-400/20'
                  : 'bg-zinc-800 text-zinc-500 hover:bg-zinc-700'
              }`}
              title={isActive ? 'Disable' : 'Enable'}
            >
              {isActive ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <h3 className="font-medium text-white mb-1 truncate">{agent.name}</h3>

        <div className="flex items-center gap-3 text-xs text-zinc-500">
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3" />
            {agent.run_count} runs
          </span>
          <span className={successRate >= 80 ? 'text-emerald-400' : successRate >= 50 ? 'text-orange-400' : 'text-red-400'}>
            {successRate}% success
          </span>
        </div>

        {agent.total_time_saved_seconds > 0 && (
          <div className="mt-2 text-xs text-cyan-400">
            <Clock className="w-3 h-3 inline mr-1" />
            {Math.round(agent.total_time_saved_seconds / 60)}m saved
          </div>
        )}
      </div>
    </motion.div>
  );
}

// Activity Item Component
function ActivityItem({
  event,
}: {
  event: {
    id: string;
    app_name: string | null;
    window_title?: string | null;
    timestamp: string;
    category?: string | null;
  };
}) {
  const timeAgo = useMemo(() => {
    const diff = Date.now() - new Date(event.timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }, [event.timestamp]);

  return (
    <div className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-zinc-800/50 transition-colors">
      <div className="p-1.5 rounded-md bg-zinc-800">
        <Monitor className="w-3.5 h-3.5 text-zinc-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-white truncate">{event.app_name || 'Unknown'}</div>
        {event.window_title && (
          <div className="text-xs text-zinc-500 truncate">{event.window_title}</div>
        )}
      </div>
      <div className="text-xs text-zinc-500 whitespace-nowrap">{timeAgo}</div>
    </div>
  );
}

// Command Palette Component
function CommandPalette({
  isOpen,
  onClose,
  onNavigate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
}) {
  const [query, setQuery] = useState('');

  const commands = [
    { id: 'agents', label: 'Go to Agents', icon: Bot, path: '/agents' },
    { id: 'analytics', label: 'View Analytics', icon: BarChart3, path: '/analytics' },
    { id: 'history', label: 'Activity History', icon: Calendar, path: '/history' },
    { id: 'chat', label: 'Open Chat', icon: MessageSquare, path: '/chat' },
    { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
    { id: 'create-agent', label: 'Create Agent', icon: Plus, path: '/agents' },
  ];

  const filtered = query
    ? commands.filter(c => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands;

  useEffect(() => {
    if (isOpen) {
      setQuery('');
    }
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg z-50"
          >
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800">
                <Search className="w-4 h-4 text-zinc-500" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Type a command or search..."
                  className="flex-1 bg-transparent text-white placeholder-zinc-500
                             outline-none text-sm"
                  autoFocus
                />
                <kbd className="px-2 py-0.5 text-xs text-zinc-500 bg-zinc-800 rounded">
                  ESC
                </kbd>
              </div>
              <div className="p-2 max-h-80 overflow-auto">
                {filtered.map((cmd) => (
                  <button
                    key={cmd.id}
                    onClick={() => { onNavigate(cmd.path); onClose(); }}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-lg
                               hover:bg-zinc-800 transition-colors text-left"
                  >
                    <cmd.icon className="w-4 h-4 text-zinc-400" />
                    <span className="text-sm text-white">{cmd.label}</span>
                    <ChevronRight className="w-4 h-4 text-zinc-600 ml-auto" />
                  </button>
                ))}
                {filtered.length === 0 && (
                  <div className="px-3 py-8 text-center text-sm text-zinc-500">
                    No commands found
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// Empty State Component
function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="p-3 rounded-xl bg-zinc-800/50 mb-4">
        <Icon className="w-6 h-6 text-zinc-500" />
      </div>
      <h3 className="text-sm font-medium text-white mb-1">{title}</h3>
      <p className="text-xs text-zinc-500 max-w-[200px] mb-4">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="px-3 py-1.5 text-xs font-medium text-cyan-400
                     bg-cyan-400/10 rounded-lg hover:bg-cyan-400/20 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// Main Dashboard Component
export default function Dashboard() {
  const navigate = useNavigate();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // WebSocket connection
  const { isConnected } = useWebSocket();

  // Data hooks
  const { data: summary } = useAnalyticsSummary();
  const { data: productivity } = useProductivity();
  const { data: timeline, refetch: refetchTimeline } = useTimeline(24);
  const { data: agents, refetch: refetchAgents } = useAgents();
  const { data: suggestions } = useSuggestions({ status: 'pending' });
  const { data: categories } = useCategories({ days: 7 });
  const { data: appUsage } = useAppUsage({ days: 7, limit: 10 });
  const { data: aiUsage } = useAIUsage(7);

  // Real-time updates
  const handleEventsCreated = useCallback(() => {
    refetchTimeline();
  }, [refetchTimeline]);

  useEventsCreated(handleEventsCreated);

  // Agent mutations
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

  // Keyboard shortcut for command palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
      if (e.key === 'Escape') {
        setCommandPaletteOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Calculated values
  const activeAgents = agents?.filter(a => a.status === 'active') || [];
  const totalTimeSaved = agents?.reduce((acc, a) => acc + a.total_time_saved_seconds, 0) ?? 0;
  const topApp = summary?.top_apps?.[0];

  // ROI calculations
  const aiCost7Days = aiUsage?.total_cost ?? 0;
  const timeSavedHours = totalTimeSaved / 3600;
  const hourlyRate = 50; // Default hourly rate for value calculation
  const valueSaved = timeSavedHours * hourlyRate;
  const roi = aiCost7Days > 0 ? ((valueSaved - aiCost7Days) / aiCost7Days) * 100 : 0;

  return (
    <>
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onNavigate={navigate}
      />

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="space-y-6 max-w-7xl mx-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
            <p className="text-sm text-zinc-500 mt-1">
              {new Date().toLocaleDateString('ru-RU', {
                weekday: 'long',
                day: 'numeric',
                month: 'long'
              })}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Connection Status */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs ${
              isConnected
                ? 'bg-emerald-400/10 text-emerald-400'
                : 'bg-red-400/10 text-red-400'
            }`}>
              {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
              {isConnected ? 'Connected' : 'Offline'}
            </div>

            {/* Command Palette Trigger */}
            <button
              onClick={() => setCommandPaletteOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg
                         bg-zinc-800 hover:bg-zinc-700 transition-colors
                         text-sm text-zinc-400"
            >
              <Command className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Search</span>
              <kbd className="hidden sm:inline px-1.5 py-0.5 text-xs bg-zinc-700 rounded">
                K
              </kbd>
            </button>
          </div>
        </div>

        {/* Metrics Grid */}
        <motion.div variants={fadeIn} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Productivity"
            value={`${Math.round(productivity?.score ?? 0)}%`}
            subValue={productivity?.productive_events
              ? `${productivity.productive_events} productive events`
              : undefined}
            icon={TrendingUp}
            accentColor="green"
            trend={productivity?.score && productivity.score >= 70 ? 'up' : 'neutral'}
          />
          <MetricCard
            label="Events Today"
            value={summary?.total_events ?? 0}
            subValue={topApp ? `Most used: ${topApp[0]}` : undefined}
            icon={Activity}
            accentColor="cyan"
          />
          <MetricCard
            label="Active Agents"
            value={`${activeAgents.length}/${agents?.length ?? 0}`}
            subValue={suggestions?.length ? `${suggestions.length} suggestions` : undefined}
            icon={Bot}
            accentColor="purple"
          />
          <MetricCard
            label="Time Saved"
            value={totalTimeSaved > 0 ? `${Math.round(totalTimeSaved / 60)}m` : '0m'}
            subValue="By automation"
            icon={Clock}
            accentColor="orange"
          />
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Agents Section */}
          <motion.div variants={fadeIn} className="lg:col-span-2">
            <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  <h2 className="font-medium text-white">Agents</h2>
                  <span className="text-xs text-zinc-500">
                    {activeAgents.length} active
                  </span>
                </div>
                <button
                  onClick={() => navigate('/agents')}
                  className="flex items-center gap-1 text-xs text-zinc-400
                             hover:text-white transition-colors"
                >
                  View all
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="p-4">
                {agents && agents.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {agents.slice(0, 4).map((agent) => (
                      <AgentCard
                        key={agent.id}
                        agent={agent}
                        onRun={() => handleRunAgent(agent.id)}
                        onToggle={() => handleToggleAgent(
                          agent.id,
                          agent.status !== 'active'
                        )}
                        onClick={() => navigate(`/agents/${agent.id}`)}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={Bot}
                    title="No agents yet"
                    description="Create your first agent to automate repetitive tasks"
                    action={{
                      label: 'Create Agent',
                      onClick: () => navigate('/agents'),
                    }}
                  />
                )}
              </div>
            </div>
          </motion.div>

          {/* Activity Feed */}
          <motion.div variants={fadeIn}>
            <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 overflow-hidden h-full">
              <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <h2 className="font-medium text-white">Activity</h2>
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                </div>
                <button
                  onClick={() => navigate('/history')}
                  className="flex items-center gap-1 text-xs text-zinc-400
                             hover:text-white transition-colors"
                >
                  History
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="p-2 max-h-[400px] overflow-auto">
                {timeline && timeline.length > 0 ? (
                  <div className="space-y-1">
                    {timeline.slice(0, 15).map((event) => (
                      <ActivityItem key={event.id} event={event} />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={Monitor}
                    title="No activity yet"
                    description="Activity will appear here as you use your devices"
                  />
                )}
              </div>
            </div>
          </motion.div>
        </div>

        {/* Bottom Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* App Usage */}
          <motion.div variants={fadeIn}>
            <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-cyan-400" />
                  <h2 className="font-medium text-white">Top Apps</h2>
                  <span className="text-xs text-zinc-500">7 days</span>
                </div>
              </div>

              <div className="p-4">
                {appUsage && appUsage.length > 0 ? (
                  <div className="space-y-3">
                    {appUsage.slice(0, 5).map((app, index) => {
                      const maxCount = appUsage[0].event_count;
                      const percentage = (app.event_count / maxCount) * 100;

                      return (
                        <div key={app.app_name} className="space-y-1.5">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-white truncate">{app.app_name}</span>
                            <span className="text-zinc-400 text-xs">
                              {app.event_count} events
                            </span>
                          </div>
                          <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${percentage}%` }}
                              transition={{ duration: 0.5, delay: index * 0.1 }}
                              className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400 rounded-full"
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <EmptyState
                    icon={BarChart3}
                    title="No app data"
                    description="App usage statistics will appear here"
                  />
                )}
              </div>
            </div>
          </motion.div>

          {/* AI Insights */}
          <motion.div variants={fadeIn}>
            <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <h2 className="font-medium text-white">AI Insights</h2>
                </div>
                <button
                  onClick={() => navigate('/chat')}
                  className="flex items-center gap-1 text-xs text-zinc-400
                             hover:text-white transition-colors"
                >
                  Ask AI
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="p-4 space-y-3">
                {productivity && productivity.score >= 70 && (
                  <div className="flex items-start gap-3 p-3 rounded-lg bg-emerald-400/5 border border-emerald-400/10">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5" />
                    <div>
                      <div className="text-sm text-white">Great productivity today!</div>
                      <div className="text-xs text-zinc-500">
                        {productivity.productive_events} productive events
                      </div>
                    </div>
                  </div>
                )}

                {suggestions && suggestions.length > 0 && (
                  <div className="flex items-start gap-3 p-3 rounded-lg bg-cyan-400/5 border border-cyan-400/10">
                    <Sparkles className="w-4 h-4 text-cyan-400 mt-0.5" />
                    <div>
                      <div className="text-sm text-white">Automation opportunities</div>
                      <div className="text-xs text-zinc-500">
                        {suggestions.length} patterns detected that could be automated
                      </div>
                    </div>
                  </div>
                )}

                {categories && categories.length > 0 && (
                  <div className="flex items-start gap-3 p-3 rounded-lg bg-violet-400/5 border border-violet-400/10">
                    <BarChart3 className="w-4 h-4 text-violet-400 mt-0.5" />
                    <div>
                      <div className="text-sm text-white">Category breakdown</div>
                      <div className="text-xs text-zinc-500">
                        Top: {categories[0]?.category} ({categories[0]?.count} events)
                      </div>
                    </div>
                  </div>
                )}

                {/* ROI Card - always show if there's any usage or time saved */}
                {(aiCost7Days > 0 || totalTimeSaved > 0) && (
                  <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-400/5 border border-amber-400/10">
                    <DollarSign className="w-4 h-4 text-amber-400 mt-0.5" />
                    <div className="flex-1">
                      <div className="text-sm text-white">AI ROI (7 days)</div>
                      <div className="text-xs text-zinc-500 space-y-0.5 mt-1">
                        <div>AI Cost: ${aiCost7Days.toFixed(2)}</div>
                        <div>Time Saved: {timeSavedHours.toFixed(1)}h (${valueSaved.toFixed(0)} value)</div>
                        {roi > 0 && <div className="text-emerald-400">ROI: +{roi.toFixed(0)}%</div>}
                        {roi <= 0 && aiCost7Days > 0 && <div className="text-zinc-400">ROI: Building up...</div>}
                      </div>
                    </div>
                  </div>
                )}

                {(!productivity || productivity.score < 70) &&
                 (!suggestions || suggestions.length === 0) &&
                 (!categories || categories.length === 0) &&
                 aiCost7Days === 0 && totalTimeSaved === 0 && (
                  <EmptyState
                    icon={Sparkles}
                    title="Gathering insights"
                    description="AI insights will appear as more data is collected"
                  />
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </>
  );
}

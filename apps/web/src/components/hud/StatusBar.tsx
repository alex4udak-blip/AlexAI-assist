import { motion } from 'framer-motion';
import { Circle } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';

interface StatusBarProps {
  focusTime?: number; // minutes
  activeAgents?: number;
  totalAgents?: number;
  systemHealth?: 'healthy' | 'warning' | 'critical';
  lastEventMinutesAgo?: number;
  syncStatus?: 'synced' | 'syncing' | 'stale';
}

export function StatusBar({
  focusTime = 0,
  activeAgents = 0,
  totalAgents = 0,
  lastEventMinutesAgo = 0,
}: StatusBarProps) {
  const { isConnected } = useWebSocket();

  const formatFocusTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const getHealthConfig = () => {
    if (!isConnected) {
      return {
        dotColor: 'bg-red-500',
        label: 'Disconnected',
      };
    }
    if (lastEventMinutesAgo > 30) {
      return {
        dotColor: 'bg-amber-500',
        label: 'No data',
      };
    }
    if (lastEventMinutesAgo > 5) {
      return {
        dotColor: 'bg-amber-500',
        label: 'Idle',
      };
    }
    return {
      dotColor: 'bg-emerald-500',
      label: 'Active',
    };
  };

  const health = getHealthConfig();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="flex items-center justify-between gap-6 px-5 py-3 rounded-xl
                 bg-zinc-900/50 border border-zinc-800"
    >
      {/* Focus Status */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2">
          <Circle className="w-2 h-2 fill-emerald-500 text-emerald-500" />
          <span className="text-xs text-zinc-400">Focus</span>
        </div>
        <span className="text-sm font-medium text-zinc-200 tabular-nums">
          {focusTime > 0 ? formatFocusTime(focusTime) : '--'}
        </span>
      </div>

      <div className="w-px h-4 bg-zinc-800" />

      {/* Active Agents */}
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-xs text-zinc-400">Agents</span>
        <span className="text-sm font-medium text-zinc-200 tabular-nums">
          {activeAgents}/{totalAgents}
        </span>
      </div>

      <div className="w-px h-4 bg-zinc-800" />

      {/* System Health */}
      <div className="flex items-center gap-2 min-w-0">
        <div className={`w-1.5 h-1.5 rounded-full ${health.dotColor}`} />
        <span className="text-sm text-zinc-300">{health.label}</span>
      </div>

      {/* Connection indicator */}
      <div className="flex items-center gap-1.5 ml-auto">
        <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-red-500'}`} />
        <span className="text-xs text-zinc-500">{isConnected ? 'Connected' : 'Offline'}</span>
      </div>
    </motion.div>
  );
}

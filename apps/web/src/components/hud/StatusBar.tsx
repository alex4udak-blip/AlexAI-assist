import { motion } from 'framer-motion';
import { Activity, Shield, Wifi, WifiOff } from 'lucide-react';
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
  systemHealth = 'healthy',
  lastEventMinutesAgo = 0,
  syncStatus = 'synced',
}: StatusBarProps) {
  const { isConnected } = useWebSocket();

  const formatFocusTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}ч ${mins}м`;
    }
    return `${mins}м`;
  };

  // More descriptive health config with tooltips
  const getHealthConfig = () => {
    if (!isConnected) {
      return {
        color: 'bg-status-error',
        glow: 'shadow-glow-orange',
        label: 'Нет связи',
        tooltip: 'WebSocket отключен'
      };
    }
    if (lastEventMinutesAgo > 30) {
      return {
        color: 'bg-status-warning',
        glow: 'shadow-glow-orange',
        label: 'Нет данных',
        tooltip: `Последнее событие ${lastEventMinutesAgo}м назад`
      };
    }
    if (lastEventMinutesAgo > 5) {
      return {
        color: 'bg-status-warning',
        glow: 'shadow-glow-orange',
        label: 'Ожидание',
        tooltip: `Последнее событие ${lastEventMinutesAgo}м назад`
      };
    }
    return {
      color: 'bg-status-success',
      glow: 'shadow-glow-green',
      label: 'Активно',
      tooltip: 'Данные поступают в реальном времени'
    };
  };

  const health = getHealthConfig();

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl
                 bg-bg-secondary/80 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow overflow-hidden"
    >
      {/* Focus Status */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <div className="relative flex-shrink-0">
          <div className="w-9 h-9 rounded-lg bg-hud-cyan/10 flex items-center justify-center
                          border border-hud-cyan/30">
            <Activity className="w-4 h-4 text-hud-cyan" />
          </div>
          <span className="absolute -top-1 -right-1 w-2 h-2 bg-status-success rounded-full
                          animate-pulse-glow" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-text-muted uppercase tracking-wider font-mono">Статус</p>
          <p className="text-xs font-medium text-text-primary truncate">
            {focusTime > 0 ? `В фокусе ${formatFocusTime(focusTime)}` : 'Ожидание'}
          </p>
        </div>
      </div>

      {/* Active Agents */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <div className="flex items-center gap-1 flex-shrink-0">
          {[...Array(Math.min(totalAgents, 5))].map((_, i) => (
            <motion.div
              key={i}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: i * 0.1 }}
              className={`w-1.5 h-1.5 rounded-full ${
                i < activeAgents
                  ? 'bg-status-success animate-pulse-glow'
                  : 'bg-text-muted/30'
              }`}
            />
          ))}
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-text-muted uppercase tracking-wider font-mono">Агенты</p>
          <p className="text-xs font-medium text-text-primary font-mono truncate">
            {activeAgents}/{totalAgents}
          </p>
        </div>
      </div>

      {/* System Health */}
      <div className="flex items-center gap-2 min-w-0 flex-1 group relative">
        <div className={`w-9 h-9 rounded-lg ${health.color}/10 flex items-center justify-center
                        border ${health.color}/30 flex-shrink-0`}>
          <Shield className={`w-4 h-4 ${
            health.color.includes('success') ? 'text-status-success' :
            health.color.includes('warning') ? 'text-status-warning' : 'text-status-error'
          }`} />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-text-muted uppercase tracking-wider font-mono">Система</p>
          <p className="text-xs font-medium text-text-primary truncate">{health.label}</p>
        </div>
        {/* Tooltip */}
        <div className="absolute left-0 top-full mt-1 px-2 py-1 bg-bg-tertiary rounded text-[10px]
                        text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity
                        pointer-events-none whitespace-nowrap z-50 border border-border-subtle">
          {health.tooltip}
        </div>
      </div>

      {/* Connection Status */}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        {isConnected ? (
          <>
            <Wifi className="w-3.5 h-3.5 text-status-success" />
            <span className="text-[10px] text-status-success font-mono hidden sm:inline">OK</span>
          </>
        ) : (
          <>
            <WifiOff className="w-3.5 h-3.5 text-status-error" />
            <span className="text-[10px] text-status-error font-mono hidden sm:inline">OFF</span>
          </>
        )}
      </div>
    </motion.div>
  );
}

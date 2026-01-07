import { motion } from 'framer-motion';
import { Activity, Bot, Shield, Wifi, WifiOff } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';

interface StatusBarProps {
  focusTime?: number; // minutes
  activeAgents?: number;
  totalAgents?: number;
  systemHealth?: 'healthy' | 'warning' | 'critical';
}

export function StatusBar({
  focusTime = 0,
  activeAgents = 0,
  totalAgents = 0,
  systemHealth = 'healthy',
}: StatusBarProps) {
  const { connected } = useWebSocket();

  const formatFocusTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}ч ${mins}м`;
    }
    return `${mins}м`;
  };

  const healthConfig = {
    healthy: { color: 'bg-status-success', glow: 'shadow-glow-green', label: 'Система OK' },
    warning: { color: 'bg-status-warning', glow: 'shadow-glow-orange', label: 'Внимание' },
    critical: { color: 'bg-status-error', glow: 'shadow-glow-orange', label: 'Критично' },
  };

  const health = healthConfig[systemHealth];

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-between px-4 py-3 rounded-xl
                 bg-bg-secondary/80 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow"
    >
      {/* Focus Status */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <div className="w-10 h-10 rounded-lg bg-hud-cyan/10 flex items-center justify-center
                          border border-hud-cyan/30">
            <Activity className="w-5 h-5 text-hud-cyan" />
          </div>
          <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-status-success rounded-full
                          animate-pulse-glow" />
        </div>
        <div>
          <p className="text-xs text-text-muted uppercase tracking-wider font-mono">Статус</p>
          <p className="text-sm font-medium text-text-primary">
            {focusTime > 0 ? `В фокусе ${formatFocusTime(focusTime)}` : 'Ожидание'}
          </p>
        </div>
      </div>

      {/* Active Agents */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          {[...Array(Math.min(totalAgents, 5))].map((_, i) => (
            <motion.div
              key={i}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: i * 0.1 }}
              className={`w-2 h-2 rounded-full ${
                i < activeAgents
                  ? 'bg-status-success animate-pulse-glow'
                  : 'bg-text-muted/30'
              }`}
            />
          ))}
        </div>
        <div>
          <p className="text-xs text-text-muted uppercase tracking-wider font-mono">Агенты</p>
          <p className="text-sm font-medium text-text-primary font-mono">
            {activeAgents}/{totalAgents} online
          </p>
        </div>
      </div>

      {/* System Health */}
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg ${health.color}/10 flex items-center justify-center
                        border ${health.color}/30`}>
          <Shield className={`w-5 h-5 ${
            systemHealth === 'healthy' ? 'text-status-success' :
            systemHealth === 'warning' ? 'text-status-warning' : 'text-status-error'
          }`} />
        </div>
        <div>
          <p className="text-xs text-text-muted uppercase tracking-wider font-mono">Система</p>
          <p className="text-sm font-medium text-text-primary">{health.label}</p>
        </div>
      </div>

      {/* Connection Status */}
      <div className="flex items-center gap-2">
        {connected ? (
          <>
            <Wifi className="w-4 h-4 text-status-success" />
            <span className="text-xs text-status-success font-mono">CONNECTED</span>
          </>
        ) : (
          <>
            <WifiOff className="w-4 h-4 text-status-error" />
            <span className="text-xs text-status-error font-mono">OFFLINE</span>
          </>
        )}
      </div>
    </motion.div>
  );
}

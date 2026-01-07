import { motion } from 'framer-motion';
import { Bot, Play, Pause, AlertTriangle, CheckCircle, Zap } from 'lucide-react';
import type { Agent } from '../../lib/api';

interface AgentGridProps {
  agents: Agent[];
  onRunAgent?: (id: string) => void;
  onToggleAgent?: (id: string, enable: boolean) => void;
}

function AgentCard({
  agent,
  onRun,
  onToggle,
  index,
}: {
  agent: Agent;
  onRun?: () => void;
  onToggle?: (enable: boolean) => void;
  index: number;
}) {
  const isActive = agent.status === 'active';
  const hasError = agent.status === 'error' || agent.last_error;

  const statusConfig = {
    active: { color: 'text-status-success', bg: 'bg-status-success', label: 'Работает' },
    disabled: { color: 'text-text-muted', bg: 'bg-text-muted', label: 'Выключен' },
    error: { color: 'text-status-error', bg: 'bg-status-error', label: 'Ошибка' },
    draft: { color: 'text-status-warning', bg: 'bg-status-warning', label: 'Черновик' },
  };

  const status = statusConfig[agent.status as keyof typeof statusConfig] || statusConfig.draft;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ scale: 1.02 }}
      className={`relative p-4 rounded-xl border backdrop-blur-md transition-all duration-200
                  ${isActive
                    ? 'bg-hud-gradient border-hud-cyan/30 shadow-hud-sm'
                    : hasError
                    ? 'bg-status-error/5 border-status-error/30'
                    : 'bg-bg-secondary/60 border-border-subtle'
                  }`}
    >
      {/* Pulse indicator for active agents */}
      {isActive && (
        <div className="absolute top-3 right-3">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-status-success opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-status-success" />
          </span>
        </div>
      )}

      {/* Agent Icon & Name */}
      <div className="flex items-start gap-3 mb-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center
                        ${isActive ? 'bg-hud-cyan/20' : 'bg-bg-tertiary'}`}>
          <Bot className={`w-5 h-5 ${isActive ? 'text-hud-cyan' : 'text-text-muted'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-text-primary truncate">{agent.name}</h4>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${status.bg}`} />
            <span className={`text-xs font-mono ${status.color}`}>{status.label}</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center p-2 rounded-lg bg-bg-primary/50">
          <p className="text-lg font-mono font-bold text-text-primary">{agent.run_count}</p>
          <p className="text-[10px] text-text-muted uppercase">Runs</p>
        </div>
        <div className="text-center p-2 rounded-lg bg-bg-primary/50">
          <p className="text-lg font-mono font-bold text-status-success">
            {agent.run_count > 0 ? Math.round((agent.success_count / agent.run_count) * 100) : 0}%
          </p>
          <p className="text-[10px] text-text-muted uppercase">Success</p>
        </div>
        <div className="text-center p-2 rounded-lg bg-bg-primary/50">
          <p className="text-lg font-mono font-bold text-hud-cyan">
            {Math.round(agent.total_time_saved_seconds / 60)}м
          </p>
          <p className="text-[10px] text-text-muted uppercase">Saved</p>
        </div>
      </div>

      {/* Last action */}
      {agent.last_error ? (
        <div className="flex items-center gap-2 text-xs text-status-error mb-3">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span className="truncate">{agent.last_error}</span>
        </div>
      ) : agent.last_run_at ? (
        <div className="flex items-center gap-2 text-xs text-text-muted mb-3">
          <CheckCircle className="w-3.5 h-3.5 text-status-success" />
          <span>Последний запуск успешен</span>
        </div>
      ) : null}

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={onRun}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg
                     bg-hud-cyan/10 text-hud-cyan text-sm font-medium
                     hover:bg-hud-cyan/20 transition-colors"
        >
          <Zap className="w-4 h-4" />
          Запуск
        </button>
        <button
          onClick={() => onToggle?.(!isActive)}
          className={`p-2 rounded-lg transition-colors ${
            isActive
              ? 'bg-status-warning/10 text-status-warning hover:bg-status-warning/20'
              : 'bg-status-success/10 text-status-success hover:bg-status-success/20'
          }`}
        >
          {isActive ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        </button>
      </div>
    </motion.div>
  );
}

export function AgentGrid({ agents, onRunAgent, onToggleAgent }: AgentGridProps) {
  if (agents.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="p-8 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                   shadow-inner-glow flex flex-col items-center justify-center"
      >
        <Bot className="w-12 h-12 text-text-muted mb-3" />
        <p className="text-text-muted">Нет активных агентов</p>
        <p className="text-xs text-text-muted mt-1">Создайте первого агента</p>
      </motion.div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {agents.map((agent, index) => (
        <AgentCard
          key={agent.id}
          agent={agent}
          index={index}
          onRun={() => onRunAgent?.(agent.id)}
          onToggle={(enable) => onToggleAgent?.(agent.id, enable)}
        />
      ))}
    </div>
  );
}

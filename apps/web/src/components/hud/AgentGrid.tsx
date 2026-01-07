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
      className={`relative p-3 rounded-xl border backdrop-blur-md transition-all duration-200 overflow-hidden
                  ${isActive
                    ? 'bg-hud-gradient border-hud-cyan/30 shadow-hud-sm'
                    : hasError
                    ? 'bg-status-error/5 border-status-error/30'
                    : 'bg-bg-secondary/60 border-border-subtle'
                  }`}
    >
      {/* Pulse indicator for active agents */}
      {isActive && (
        <div className="absolute top-2 right-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-status-success opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-status-success" />
          </span>
        </div>
      )}

      {/* Agent Icon & Name */}
      <div className="flex items-start gap-2 mb-2">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
                        ${isActive ? 'bg-hud-cyan/20' : 'bg-bg-tertiary'}`}>
          <Bot className={`w-4 h-4 ${isActive ? 'text-hud-cyan' : 'text-text-muted'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-text-primary truncate">{agent.name}</h4>
          <div className="flex items-center gap-1">
            <span className={`w-1.5 h-1.5 rounded-full ${status.bg} flex-shrink-0`} />
            <span className={`text-[10px] font-mono ${status.color}`}>{status.label}</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-1.5 mb-2">
        <div className="text-center p-1.5 rounded-lg bg-bg-primary/50 overflow-hidden">
          <p className="text-sm font-mono font-bold text-text-primary">{agent.run_count}</p>
          <p className="text-[9px] text-text-muted uppercase truncate">Runs</p>
        </div>
        <div className="text-center p-1.5 rounded-lg bg-bg-primary/50 overflow-hidden">
          <p className="text-sm font-mono font-bold text-status-success">
            {agent.run_count > 0 ? Math.round((agent.success_count / agent.run_count) * 100) : 0}%
          </p>
          <p className="text-[9px] text-text-muted uppercase truncate">OK</p>
        </div>
        <div className="text-center p-1.5 rounded-lg bg-bg-primary/50 overflow-hidden">
          <p className="text-sm font-mono font-bold text-hud-cyan">
            {Math.round(agent.total_time_saved_seconds / 60)}м
          </p>
          <p className="text-[9px] text-text-muted uppercase truncate">Save</p>
        </div>
      </div>

      {/* Last action */}
      {agent.last_error ? (
        <div className="flex items-center gap-1.5 text-[10px] text-status-error mb-2 min-w-0">
          <AlertTriangle className="w-3 h-3 flex-shrink-0" />
          <span className="truncate">{agent.last_error}</span>
        </div>
      ) : agent.last_run_at ? (
        <div className="flex items-center gap-1.5 text-[10px] text-text-muted mb-2">
          <CheckCircle className="w-3 h-3 text-status-success flex-shrink-0" />
          <span className="truncate">Успешно</span>
        </div>
      ) : null}

      {/* Actions */}
      <div className="flex items-center gap-1.5">
        <button
          onClick={onRun}
          className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg
                     bg-hud-cyan/10 text-hud-cyan text-xs font-medium
                     hover:bg-hud-cyan/20 transition-colors"
        >
          <Zap className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="truncate">Запуск</span>
        </button>
        <button
          onClick={() => onToggle?.(!isActive)}
          className={`p-1.5 rounded-lg transition-colors flex-shrink-0 ${
            isActive
              ? 'bg-status-warning/10 text-status-warning hover:bg-status-warning/20'
              : 'bg-status-success/10 text-status-success hover:bg-status-success/20'
          }`}
        >
          {isActive ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
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
        className="p-6 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                   shadow-inner-glow flex flex-col items-center justify-center overflow-hidden"
      >
        <Bot className="w-10 h-10 text-text-muted mb-2" />
        <p className="text-sm text-text-muted text-center">Нет агентов</p>
        <p className="text-xs text-text-muted mt-1 text-center">Создайте первого</p>
      </motion.div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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

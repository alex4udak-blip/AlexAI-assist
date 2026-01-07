import { useState } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, Settings, Trash2, MoreVertical, Zap, Clock, TrendingUp } from 'lucide-react';
import { formatRelativeTime, formatDuration } from '../../lib/utils';
import type { Agent } from '../../lib/api';

interface AgentCardProps {
  agent: Agent;
  onRun?: (id: string) => void;
  onEnable?: (id: string) => void;
  onDisable?: (id: string) => void;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}

const agentColors = [
  { from: 'from-emerald-500/20', to: 'to-emerald-500/5', icon: 'text-emerald-400' },
  { from: 'from-blue-500/20', to: 'to-blue-500/5', icon: 'text-blue-400' },
  { from: 'from-purple-500/20', to: 'to-purple-500/5', icon: 'text-purple-400' },
  { from: 'from-amber-500/20', to: 'to-amber-500/5', icon: 'text-amber-400' },
  { from: 'from-rose-500/20', to: 'to-rose-500/5', icon: 'text-rose-400' },
];

export function AgentCard({
  agent,
  onRun,
  onEnable,
  onDisable,
  onEdit,
  onDelete,
}: AgentCardProps) {
  const [showMenu, setShowMenu] = useState(false);

  // Get consistent color based on agent name
  const colorIndex = agent.name.length % agentColors.length;
  const colors = agentColors[colorIndex];

  const successRate = agent.run_count > 0
    ? ((agent.success_count / agent.run_count) * 100).toFixed(0)
    : 0;

  return (
    <motion.div
      whileHover={{ y: -2 }}
      className="group relative p-5 rounded-2xl border border-border-subtle
                 bg-gradient-to-br from-white/[0.02] to-transparent
                 hover:border-border-default hover:bg-white/[0.03]
                 transition-all duration-200"
    >
      {/* Glow effect on hover */}
      <div className="absolute inset-0 rounded-2xl bg-glow-gradient
                      opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

      <div className="relative">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-4">
            {/* Icon */}
            <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${colors.from} ${colors.to}
                            flex items-center justify-center shrink-0`}>
              <Zap className={`w-6 h-6 ${colors.icon}`} />
            </div>

            <div>
              {/* Name & Status */}
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold text-text-primary">{agent.name}</h3>
                <div className={`w-2 h-2 rounded-full ${
                  agent.status === 'active' ? 'bg-status-success' :
                  agent.status === 'disabled' ? 'bg-status-error' : 'bg-status-warning'
                }`} />
              </div>
              {/* Description */}
              <p className="text-sm text-text-tertiary line-clamp-2">
                {agent.description || 'Нет описания'}
              </p>
            </div>
          </div>

          {/* Menu */}
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(!showMenu);
              }}
              className="p-2 rounded-lg text-text-tertiary hover:text-text-primary
                         hover:bg-white/[0.05] transition-colors opacity-0 group-hover:opacity-100"
            >
              <MoreVertical className="w-5 h-5" />
            </button>

            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute right-0 top-10 w-44 bg-bg-elevated border border-border-default
                             rounded-xl shadow-lg py-1 z-20 overflow-hidden"
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit?.(agent.id);
                      setShowMenu(false);
                    }}
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-sm
                               text-text-secondary hover:text-text-primary hover:bg-white/[0.05]"
                  >
                    <Settings className="w-4 h-4" />
                    Редактировать
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete?.(agent.id);
                      setShowMenu(false);
                    }}
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-sm
                               text-status-error hover:bg-status-error/10"
                  >
                    <Trash2 className="w-4 h-4" />
                    Удалить
                  </button>
                </motion.div>
              </>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="p-3 rounded-xl bg-white/[0.02]">
            <p className="text-xs text-text-muted mb-1">Запусков</p>
            <p className="text-lg font-semibold text-text-primary">{agent.run_count}</p>
          </div>
          <div className="p-3 rounded-xl bg-white/[0.02]">
            <p className="text-xs text-text-muted mb-1">Успешность</p>
            <p className="text-lg font-semibold text-text-primary">{successRate}%</p>
          </div>
          <div className="p-3 rounded-xl bg-white/[0.02]">
            <p className="text-xs text-text-muted mb-1">Сэкономлено</p>
            <p className="text-lg font-semibold text-text-primary">
              {formatDuration(agent.total_time_saved_seconds)}
            </p>
          </div>
        </div>

        {/* Last run + Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Clock className="w-3.5 h-3.5" />
            {agent.last_run_at ? (
              <span>Последний: {formatRelativeTime(agent.last_run_at)}</span>
            ) : (
              <span>Ещё не запускался</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {agent.status === 'active' ? (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDisable?.(agent.id);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                           text-text-tertiary text-sm font-medium
                           hover:bg-white/[0.05] hover:text-status-warning transition-colors"
              >
                <Pause className="w-4 h-4" />
                Стоп
              </button>
            ) : (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onEnable?.(agent.id);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                           text-text-tertiary text-sm font-medium
                           hover:bg-white/[0.05] hover:text-status-success transition-colors"
              >
                <Play className="w-4 h-4" />
                Вкл
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRun?.(agent.id);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                         bg-accent-primary/10 text-accent-primary text-sm font-medium
                         hover:bg-accent-primary/20 transition-colors"
            >
              <TrendingUp className="w-4 h-4" />
              Запуск
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

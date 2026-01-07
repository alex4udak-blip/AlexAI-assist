import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, Play, Pause, PlayCircle, Clock, ChevronRight, Bot } from 'lucide-react';
import type { Agent } from '../../lib/api';

interface AgentsListProps {
  agents?: Agent[];
  loading?: boolean;
  onRun?: (id: string) => void;
  onToggle?: (id: string, enabled: boolean) => void;
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export function AgentsList({ agents, loading, onRun, onToggle }: AgentsListProps) {
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-6 w-32 skeleton" />
          <div className="h-8 w-24 skeleton rounded-lg" />
        </div>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="p-4 rounded-xl border border-border-subtle bg-surface-primary">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl skeleton" />
                <div className="flex-1">
                  <div className="h-5 w-32 skeleton mb-2" />
                  <div className="h-4 w-48 skeleton mb-3" />
                  <div className="h-3 w-24 skeleton" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary tracking-tight">
          Активные агенты
        </h2>
        <Link
          to="/agents"
          className="flex items-center gap-1 text-sm text-text-tertiary hover:text-text-primary transition-colors"
        >
          Все агенты
          <ChevronRight className="w-4 h-4" />
        </Link>
      </div>

      {agents && agents.length > 0 ? (
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="space-y-3"
        >
          {agents.slice(0, 4).map((agent) => (
            <motion.div
              key={agent.id}
              variants={item}
              whileHover={{ y: -2 }}
              className="group p-4 rounded-xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent
                         hover:border-border-default hover:bg-white/[0.03] transition-all duration-200 cursor-pointer"
            >
              <div className="flex items-start gap-4">
                {/* Agent Icon */}
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-500/5
                                flex items-center justify-center shrink-0">
                  <Zap className="w-6 h-6 text-emerald-400" />
                </div>

                <div className="flex-1 min-w-0">
                  {/* Name & Status */}
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-medium text-text-primary truncate">{agent.name}</h4>
                    <div className={`w-1.5 h-1.5 rounded-full ${agent.status === 'active' ? 'bg-status-success' : 'bg-text-muted'}`} />
                  </div>

                  {/* Description */}
                  <p className="text-sm text-text-tertiary line-clamp-1 mb-3">
                    {agent.description || 'Нет описания'}
                  </p>

                  {/* Stats */}
                  <div className="flex items-center gap-4 text-xs text-text-muted">
                    <span className="flex items-center gap-1">
                      <PlayCircle className="w-3.5 h-3.5" />
                      {agent.run_count} запусков
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {agent.success_count} успешных
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {agent.status === 'active' ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggle?.(agent.id, false);
                      }}
                      className="p-2 rounded-lg text-text-tertiary hover:text-status-warning hover:bg-white/[0.05] transition-colors"
                      title="Приостановить"
                    >
                      <Pause className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggle?.(agent.id, true);
                      }}
                      className="p-2 rounded-lg text-text-tertiary hover:text-status-success hover:bg-white/[0.05] transition-colors"
                      title="Запустить"
                    >
                      <Play className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRun?.(agent.id);
                    }}
                    className="p-2 rounded-lg text-text-tertiary hover:text-accent-primary hover:bg-white/[0.05] transition-colors"
                    title="Выполнить сейчас"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <div className="p-8 rounded-2xl border border-border-subtle bg-surface-primary text-center">
          <Bot className="w-10 h-10 text-text-muted mx-auto mb-3" />
          <p className="text-text-tertiary text-sm">Нет активных агентов</p>
          <Link
            to="/agents"
            className="inline-flex items-center gap-1 mt-3 text-sm text-accent-primary hover:underline"
          >
            Создать агента
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      )}
    </div>
  );
}

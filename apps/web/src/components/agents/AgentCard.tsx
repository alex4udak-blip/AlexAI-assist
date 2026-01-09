import { useState } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, Settings, Trash2, MoreVertical, Clock, TrendingUp, Activity } from 'lucide-react';
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

export function AgentCard({
  agent,
  onRun,
  onEnable,
  onDisable,
  onEdit,
  onDelete,
}: AgentCardProps) {
  const [showMenu, setShowMenu] = useState(false);

  const successRate = agent.run_count > 0
    ? ((agent.success_count / agent.run_count) * 100).toFixed(0)
    : 0;

  // Status-based colors: green for active, blue for idle, orange for error
  const statusColors = {
    active: {
      border: 'border-green-500/50',
      glow: 'shadow-[0_0_15px_rgba(34,197,94,0.3)]',
      text: 'text-green-400',
      bg: 'bg-green-500/10',
      pulse: 'bg-green-500',
    },
    disabled: {
      border: 'border-blue-500/30',
      glow: 'shadow-[0_0_10px_rgba(59,130,246,0.2)]',
      text: 'text-blue-400',
      bg: 'bg-blue-500/10',
      pulse: 'bg-blue-500',
    },
    draft: {
      border: 'border-orange-500/30',
      glow: 'shadow-[0_0_10px_rgba(249,115,22,0.2)]',
      text: 'text-orange-400',
      bg: 'bg-orange-500/10',
      pulse: 'bg-orange-500',
    },
  };

  const colors = statusColors[agent.status as keyof typeof statusColors] || statusColors.draft;

  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.01 }}
      transition={{ duration: 0.2 }}
      className={`group relative p-5 rounded-xl border-2 ${colors.border}
                 bg-gradient-to-br from-black/40 via-black/20 to-transparent
                 hover:${colors.glow} backdrop-blur-sm
                 transition-all duration-300 overflow-hidden`}
    >
      {/* Holographic grid effect */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
           style={{
             backgroundImage: `
               linear-gradient(rgba(34,197,94,0.1) 1px, transparent 1px),
               linear-gradient(90deg, rgba(34,197,94,0.1) 1px, transparent 1px)
             `,
             backgroundSize: '20px 20px'
           }}
      />

      {/* Animated scan line */}
      <motion.div
        className={`absolute left-0 right-0 h-[2px] ${colors.pulse} opacity-30 blur-sm`}
        animate={{
          top: ['0%', '100%'],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: 'linear',
        }}
      />

      {/* Corner accents */}
      <div className={`absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 ${colors.border} opacity-50`} />
      <div className={`absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 ${colors.border} opacity-50`} />
      <div className={`absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 ${colors.border} opacity-50`} />
      <div className={`absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 ${colors.border} opacity-50`} />

      {/* Neon glow on active agents */}
      {agent.status === 'active' && (
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-green-500/5 via-green-400/10 to-green-500/5 rounded-xl"
          animate={{
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-4 flex-1">
            {/* Icon with holographic effect */}
            <div className={`relative w-12 h-12 rounded-lg ${colors.bg}
                            flex items-center justify-center shrink-0 overflow-hidden
                            border border-current/20`}>
              <motion.div
                className={`absolute inset-0 bg-gradient-to-br from-white/20 to-transparent`}
                animate={{
                  opacity: [0.2, 0.4, 0.2],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              />
              <Activity className={`w-6 h-6 ${colors.text} relative z-10`} />
            </div>

            <div className="flex-1 min-w-0">
              {/* Name & Status */}
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold text-text-primary truncate">{agent.name}</h3>
                {/* Pulsing status indicator */}
                <div className="relative flex items-center justify-center w-3 h-3">
                  <motion.div
                    className={`absolute w-3 h-3 rounded-full ${colors.pulse}`}
                    animate={{
                      scale: [1, 1.5, 1],
                      opacity: [0.6, 0, 0.6],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                  />
                  <div className={`w-2 h-2 rounded-full ${colors.pulse} relative z-10`} />
                </div>
              </div>
              {/* Description */}
              <p className="text-sm text-text-tertiary/80 line-clamp-2 font-light">
                {agent.description || 'Нет описания'}
              </p>
            </div>
          </div>

          {/* Menu */}
          <div className="relative ml-2">
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(!showMenu);
              }}
              className={`p-2 rounded-lg ${colors.text} bg-white/[0.03]
                         hover:bg-white/[0.08] transition-colors opacity-0 group-hover:opacity-100
                         border border-current/20`}
            >
              <MoreVertical className="w-4 h-4" />
            </motion.button>

            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: -10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  className="absolute right-0 top-10 w-44 bg-black/90 border-2 border-green-500/30
                             rounded-lg shadow-[0_0_20px_rgba(34,197,94,0.2)] py-1 z-20 overflow-hidden backdrop-blur-xl"
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit?.(agent.id);
                      setShowMenu(false);
                    }}
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-sm
                               text-text-secondary hover:text-green-400 hover:bg-green-500/10
                               transition-colors"
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
                               text-orange-400 hover:bg-orange-500/10 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    Удалить
                  </button>
                </motion.div>
              </>
            )}
          </div>
        </div>

        {/* Stats - HUD style */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className={`p-3 rounded-lg ${colors.bg} border border-current/20 backdrop-blur-sm`}>
            <p className={`text-[10px] ${colors.text} mb-1 uppercase tracking-wider font-mono`}>Runs</p>
            <p className={`text-lg font-bold ${colors.text} font-mono`}>{agent.run_count}</p>
          </div>
          <div className={`p-3 rounded-lg ${colors.bg} border border-current/20 backdrop-blur-sm`}>
            <p className={`text-[10px] ${colors.text} mb-1 uppercase tracking-wider font-mono`}>Success</p>
            <p className={`text-lg font-bold ${colors.text} font-mono`}>{successRate}%</p>
          </div>
          <div className={`p-3 rounded-lg ${colors.bg} border border-current/20 backdrop-blur-sm`}>
            <p className={`text-[10px] ${colors.text} mb-1 uppercase tracking-wider font-mono`}>Saved</p>
            <p className={`text-lg font-bold ${colors.text} font-mono`}>
              {formatDuration(agent.total_time_saved_seconds)}
            </p>
          </div>
        </div>

        {/* Last run + Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-white/[0.05]">
          <div className="flex items-center gap-2 text-xs text-text-muted font-mono">
            <Clock className="w-3.5 h-3.5" />
            {agent.last_run_at ? (
              <span>{formatRelativeTime(agent.last_run_at)}</span>
            ) : (
              <span>Never run</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {agent.status === 'active' ? (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={(e) => {
                  e.stopPropagation();
                  onDisable?.(agent.id);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                           text-orange-400 text-xs font-medium font-mono uppercase tracking-wider
                           bg-orange-500/10 border border-orange-500/30
                           hover:bg-orange-500/20 transition-colors"
              >
                <Pause className="w-3.5 h-3.5" />
                Stop
              </motion.button>
            ) : (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={(e) => {
                  e.stopPropagation();
                  onEnable?.(agent.id);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                           text-green-400 text-xs font-medium font-mono uppercase tracking-wider
                           bg-green-500/10 border border-green-500/30
                           hover:bg-green-500/20 transition-colors"
              >
                <Play className="w-3.5 h-3.5" />
                Enable
              </motion.button>
            )}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={(e) => {
                e.stopPropagation();
                onRun?.(agent.id);
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                         ${colors.text} text-xs font-medium font-mono uppercase tracking-wider
                         ${colors.bg} border border-current/30
                         hover:border-current/50 transition-all
                         shadow-[0_0_10px_rgba(34,197,94,0.1)]`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              Run
            </motion.button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

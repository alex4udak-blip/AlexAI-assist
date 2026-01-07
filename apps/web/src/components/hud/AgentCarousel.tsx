import { useState, useRef } from 'react';
import { motion, PanInfo, useAnimation } from 'framer-motion';
import { Play, Pause, Clock, CheckCircle, ChevronRight } from 'lucide-react';

interface Agent {
  id: string;
  name: string;
  description?: string | null;
  status: string;
  run_count: number;
  success_count: number;
  error_count: number;
  total_time_saved_seconds: number;
  last_run_at?: string | null;
}

interface AgentCarouselProps {
  agents: Agent[];
  onRunAgent: (id: string) => void;
  onToggleAgent: (id: string, enabled: boolean) => void;
  onViewDetails?: (id: string) => void;
}

export function AgentCarousel({
  agents,
  onRunAgent,
  onToggleAgent,
  onViewDetails,
}: AgentCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const controls = useAnimation();
  const containerRef = useRef<HTMLDivElement>(null);

  const handleDragEnd = (_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    const threshold = 50;
    if (info.offset.x > threshold && currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    } else if (info.offset.x < -threshold && currentIndex < agents.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
    controls.start({ x: -currentIndex * 100 + '%' });
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}с`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}м`;
    return `${(seconds / 3600).toFixed(1)}ч`;
  };

  if (agents.length === 0) {
    return (
      <div className="p-6 text-center">
        <p className="text-text-muted text-sm">Нет агентов</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden">
      <motion.div
        ref={containerRef}
        className="flex"
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.1}
        onDragEnd={handleDragEnd}
        animate={controls}
        initial={{ x: 0 }}
        style={{ x: `-${currentIndex * 100}%` }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        {agents.map((agent) => {
          const isActive = agent.status === 'active';
          const successRate = agent.run_count > 0
            ? Math.round((agent.success_count / agent.run_count) * 100)
            : 0;

          return (
            <motion.div
              key={agent.id}
              className="w-full flex-shrink-0 px-4"
              onClick={() => onViewDetails?.(agent.id)}
            >
              <div className={`p-5 rounded-xl border transition-all touch-pan-y
                             ${isActive
                               ? 'bg-hud-cyan/5 border-hud-cyan/30'
                               : 'bg-bg-secondary/60 border-border-subtle'
                             }`}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-status-success animate-pulse' : 'bg-text-muted'}`} />
                      <h3 className="font-medium text-text-primary truncate">{agent.name}</h3>
                    </div>
                    {agent.description && (
                      <p className="text-xs text-text-muted mt-1 line-clamp-2">
                        {agent.description}
                      </p>
                    )}
                  </div>
                  <ChevronRight className="w-5 h-5 text-text-muted flex-shrink-0" />
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="text-center p-2 rounded-lg bg-bg-primary/50">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <CheckCircle className="w-3.5 h-3.5 text-status-success" />
                    </div>
                    <p className="text-lg font-mono font-bold text-text-primary">{successRate}%</p>
                    <p className="text-[10px] text-text-muted">Успех</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-bg-primary/50">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <Play className="w-3.5 h-3.5 text-hud-cyan" />
                    </div>
                    <p className="text-lg font-mono font-bold text-text-primary">{agent.run_count}</p>
                    <p className="text-[10px] text-text-muted">Запуски</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-bg-primary/50">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <Clock className="w-3.5 h-3.5 text-ring-outer" />
                    </div>
                    <p className="text-lg font-mono font-bold text-text-primary">
                      {formatTime(agent.total_time_saved_seconds)}
                    </p>
                    <p className="text-[10px] text-text-muted">Сохранено</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRunAgent(agent.id);
                    }}
                    className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg
                               bg-hud-gradient text-white font-medium text-sm
                               active:scale-95 transition-transform touch-manipulation"
                  >
                    <Play className="w-4 h-4" />
                    Запустить
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleAgent(agent.id, !isActive);
                    }}
                    className={`px-4 py-3 rounded-lg font-medium text-sm
                               active:scale-95 transition-transform touch-manipulation
                               ${isActive
                                 ? 'bg-status-warning/10 text-status-warning border border-status-warning/20'
                                 : 'bg-status-success/10 text-status-success border border-status-success/20'
                               }`}
                  >
                    {isActive ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Dots Indicator */}
      {agents.length > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          {agents.map((_, index) => (
            <button
              key={index}
              onClick={() => {
                setCurrentIndex(index);
                controls.start({ x: -index * 100 + '%' });
              }}
              className={`w-2 h-2 rounded-full transition-all touch-manipulation
                         ${index === currentIndex
                           ? 'bg-hud-cyan w-6'
                           : 'bg-white/20'
                         }`}
              style={{ minWidth: '8px', minHeight: '8px' }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

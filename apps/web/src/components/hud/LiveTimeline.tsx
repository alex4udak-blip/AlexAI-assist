import { motion } from 'framer-motion';
import { useRef, useEffect } from 'react';
import { Monitor, Bot, Clock } from 'lucide-react';

interface TimelineEvent {
  id: string;
  type: 'app' | 'agent';
  name: string;
  startTime: string; // ISO string
  endTime?: string;
  category?: string;
  color?: string;
}

interface LiveTimelineProps {
  events: TimelineEvent[];
  startHour?: number;
  endHour?: number;
}

const categoryColors: Record<string, string> = {
  coding: '#06b6d4',
  browsing: '#3b82f6',
  communication: '#8b5cf6',
  writing: '#10b981',
  design: '#f59e0b',
  other: '#6b7280',
};

export function LiveTimeline({
  events,
  startHour = 6,
  endHour = 23,
}: LiveTimelineProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const hours = Array.from({ length: endHour - startHour + 1 }, (_, i) => startHour + i);
  const totalMinutes = (endHour - startHour + 1) * 60;

  // Auto-scroll to current time
  useEffect(() => {
    if (scrollRef.current) {
      const now = new Date();
      const currentHour = now.getHours();
      const currentMinute = now.getMinutes();
      const minutesSinceStart = (currentHour - startHour) * 60 + currentMinute;
      const scrollPercent = minutesSinceStart / totalMinutes;
      const scrollPosition = scrollRef.current.scrollWidth * scrollPercent - scrollRef.current.clientWidth / 2;
      scrollRef.current.scrollTo({ left: Math.max(0, scrollPosition), behavior: 'smooth' });
    }
  }, [startHour, totalMinutes]);

  const getEventPosition = (startTime: string) => {
    const date = new Date(startTime);
    const minutes = (date.getHours() - startHour) * 60 + date.getMinutes();
    return (minutes / totalMinutes) * 100;
  };

  const getEventWidth = (startTime: string, endTime?: string) => {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const durationMinutes = (end.getTime() - start.getTime()) / 60000;
    return Math.max((durationMinutes / totalMinutes) * 100, 0.5); // Min 0.5% width
  };

  // Current time indicator
  const now = new Date();
  const currentPosition = ((now.getHours() - startHour) * 60 + now.getMinutes()) / totalMinutes * 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow overflow-hidden"
    >
      <div className="flex items-center justify-between gap-2 mb-3">
        <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono flex-shrink-0">
          Timeline
        </h3>
        <div className="flex items-center gap-1.5 text-[10px] text-text-muted font-mono flex-shrink-0">
          <Clock className="w-3 h-3" />
          {now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>

      <div
        ref={scrollRef}
        className="overflow-x-auto scrollbar-hide pb-2"
      >
        <div className="relative min-w-[800px] h-24">
          {/* Hour markers */}
          <div className="absolute top-0 left-0 right-0 h-6 flex">
            {hours.map((hour) => (
              <div
                key={hour}
                className="flex-1 text-xs text-text-muted font-mono border-l border-border-subtle pl-1"
              >
                {hour}:00
              </div>
            ))}
          </div>

          {/* Grid lines */}
          <div className="absolute top-6 bottom-0 left-0 right-0">
            {hours.map((hour) => (
              <div
                key={hour}
                className="absolute top-0 bottom-0 border-l border-border-subtle/50"
                style={{ left: `${((hour - startHour) / (endHour - startHour + 1)) * 100}%` }}
              />
            ))}
          </div>

          {/* Events track - Apps */}
          <div className="absolute top-8 left-0 right-0 h-7">
            {events
              .filter((e) => e.type === 'app')
              .map((event) => {
                const color = event.color || categoryColors[event.category || 'other'];
                return (
                  <motion.div
                    key={event.id}
                    initial={{ opacity: 0, scaleX: 0 }}
                    animate={{ opacity: 1, scaleX: 1 }}
                    className="absolute top-0 h-full rounded-md flex items-center px-2
                               overflow-hidden cursor-pointer group"
                    style={{
                      left: `${getEventPosition(event.startTime)}%`,
                      width: `${getEventWidth(event.startTime, event.endTime)}%`,
                      backgroundColor: `${color}20`,
                      borderLeft: `3px solid ${color}`,
                    }}
                    title={`${event.name} - ${event.category || 'other'}`}
                  >
                    <Monitor className="w-3 h-3 shrink-0" style={{ color }} />
                    <span className="ml-1 text-[10px] text-text-primary truncate">
                      {event.name}
                    </span>
                  </motion.div>
                );
              })}
          </div>

          {/* Events track - Agents */}
          <div className="absolute top-16 left-0 right-0 h-6">
            {events
              .filter((e) => e.type === 'agent')
              .map((event) => (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute top-0 w-6 h-6 rounded-lg bg-hud-cyan/20 border border-hud-cyan/40
                             flex items-center justify-center cursor-pointer hover:shadow-hud-sm
                             transition-shadow"
                  style={{
                    left: `${getEventPosition(event.startTime)}%`,
                    transform: 'translateX(-50%)',
                  }}
                  title={event.name}
                >
                  <Bot className="w-3.5 h-3.5 text-hud-cyan" />
                </motion.div>
              ))}
          </div>

          {/* Current time indicator */}
          {currentPosition >= 0 && currentPosition <= 100 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="absolute top-6 bottom-0 w-0.5 bg-status-error z-10"
              style={{ left: `${currentPosition}%` }}
            >
              <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-status-error rounded-full
                              shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
            </motion.div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-2 pt-2 border-t border-border-subtle overflow-x-auto">
        <div className="flex items-center gap-1 flex-shrink-0">
          <Monitor className="w-3 h-3 text-hud-cyan" />
          <span className="text-[10px] text-text-muted">Apps</span>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <Bot className="w-3 h-3 text-hud-cyan" />
          <span className="text-[10px] text-text-muted">Agents</span>
        </div>
        <div className="flex items-center gap-1 ml-auto flex-shrink-0">
          <div className="w-1.5 h-1.5 bg-status-error rounded-full" />
          <span className="text-[10px] text-text-muted">Now</span>
        </div>
      </div>
    </motion.div>
  );
}

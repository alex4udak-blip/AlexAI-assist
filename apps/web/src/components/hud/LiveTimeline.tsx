import { motion } from 'framer-motion';
import { useRef, useEffect, useMemo } from 'react';
import { Clock } from 'lucide-react';

interface TimelineEvent {
  id: string;
  type: 'app' | 'agent';
  name: string;
  startTime: string;
  endTime?: string;
  category?: string;
}

interface ActivityBlock {
  startTime: Date;
  endTime: Date;
  events: number;
}

interface AppTrack {
  appName: string;
  category: string;
  blocks: ActivityBlock[];
  totalMinutes: number;
}

interface LiveTimelineProps {
  events: TimelineEvent[];
  startHour?: number;
  endHour?: number;
  maxTracks?: number;
}

const categoryColors: Record<string, string> = {
  coding: '#06b6d4',
  browsing: '#3b82f6',
  communication: '#8b5cf6',
  writing: '#10b981',
  design: '#f59e0b',
  other: '#64748b',
};

const getAppColor = (appName: string, category?: string): string => {
  if (category && categoryColors[category]) {
    return categoryColors[category];
  }
  let hash = 0;
  for (let i = 0; i < appName.length; i++) {
    hash = appName.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colors = ['#06b6d4', '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#14b8a6'];
  return colors[Math.abs(hash) % colors.length];
};

export function LiveTimeline({
  events,
  startHour = 6,
  endHour = 23,
  maxTracks = 6,
}: LiveTimelineProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const hours = Array.from({ length: endHour - startHour + 1 }, (_, i) => startHour + i);
  const totalMinutes = (endHour - startHour + 1) * 60;

  // Build activity blocks for each app
  const appTracks = useMemo(() => {
    const appEvents = events.filter(e => e.type === 'app');
    if (appEvents.length === 0) return [];

    // Group by app
    const appGroups: Record<string, { events: TimelineEvent[]; category: string }> = {};
    appEvents.forEach(event => {
      if (!appGroups[event.name]) {
        appGroups[event.name] = { events: [], category: event.category || 'other' };
      }
      appGroups[event.name].events.push(event);
    });

    // Create tracks with merged activity blocks
    const tracks: AppTrack[] = Object.entries(appGroups).map(([appName, data]) => {
      // Sort by time
      const sorted = data.events
        .map(e => new Date(e.startTime))
        .sort((a, b) => a.getTime() - b.getTime());

      // Merge into continuous blocks (5 min gap tolerance)
      const blocks: ActivityBlock[] = [];
      let currentBlock: ActivityBlock | null = null;
      const GAP_TOLERANCE = 5 * 60 * 1000; // 5 minutes
      const MIN_BLOCK_DURATION = 60 * 1000; // 1 minute minimum

      sorted.forEach(eventTime => {
        const eventEnd = new Date(eventTime.getTime() + MIN_BLOCK_DURATION);

        if (!currentBlock) {
          currentBlock = { startTime: eventTime, endTime: eventEnd, events: 1 };
        } else if (eventTime.getTime() - currentBlock.endTime.getTime() <= GAP_TOLERANCE) {
          // Extend current block
          currentBlock.endTime = eventEnd;
          currentBlock.events++;
        } else {
          // Save current and start new
          blocks.push(currentBlock);
          currentBlock = { startTime: eventTime, endTime: eventEnd, events: 1 };
        }
      });

      if (currentBlock) {
        blocks.push(currentBlock);
      }

      // Calculate total active minutes
      const totalMins = blocks.reduce((sum, b) =>
        sum + (b.endTime.getTime() - b.startTime.getTime()) / 60000, 0
      );

      return {
        appName,
        category: data.category,
        blocks,
        totalMinutes: totalMins,
      };
    });

    // Sort by activity and take top N
    return tracks
      .sort((a, b) => b.totalMinutes - a.totalMinutes)
      .slice(0, maxTracks);
  }, [events, maxTracks]);

  // Auto-scroll to current time
  useEffect(() => {
    if (scrollRef.current) {
      const now = new Date();
      const minutesSinceStart = (now.getHours() - startHour) * 60 + now.getMinutes();
      const scrollPercent = minutesSinceStart / totalMinutes;
      const scrollPosition = scrollRef.current.scrollWidth * scrollPercent - scrollRef.current.clientWidth / 2;
      scrollRef.current.scrollTo({ left: Math.max(0, scrollPosition), behavior: 'smooth' });
    }
  }, [startHour, totalMinutes]);

  const getPosition = (time: Date) => {
    const minutes = (time.getHours() - startHour) * 60 + time.getMinutes();
    return Math.max(0, Math.min(100, (minutes / totalMinutes) * 100));
  };

  const getWidth = (start: Date, end: Date) => {
    const durationMinutes = (end.getTime() - start.getTime()) / 60000;
    return Math.max((durationMinutes / totalMinutes) * 100, 0.5);
  };

  const now = new Date();
  const currentPosition = getPosition(now);

  const TRACK_HEIGHT = 28;
  const HEADER_HEIGHT = 28;
  const LABEL_WIDTH = 90;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle shadow-inner-glow"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono">
          Activity Timeline
        </h3>
        <div className="flex items-center gap-1.5 text-[10px] text-text-muted font-mono">
          <Clock className="w-3 h-3" />
          {now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>

      {/* Timeline container */}
      <div className="flex">
        {/* Fixed labels column */}
        <div className="flex-shrink-0" style={{ width: LABEL_WIDTH }}>
          {/* Empty header space */}
          <div style={{ height: HEADER_HEIGHT }} />
          {/* App labels */}
          {appTracks.map((track) => {
            const color = getAppColor(track.appName, track.category);
            return (
              <div
                key={track.appName}
                className="flex items-center pr-2"
                style={{ height: TRACK_HEIGHT }}
              >
                <div
                  className="w-2 h-2 rounded-sm mr-2 flex-shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span
                  className="text-[11px] font-medium truncate"
                  style={{ color }}
                  title={track.appName}
                >
                  {track.appName}
                </span>
              </div>
            );
          })}
        </div>

        {/* Scrollable timeline */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-x-auto scrollbar-thin scrollbar-thumb-border-subtle"
        >
          <div className="relative min-w-[700px]">
            {/* Hour markers */}
            <div className="flex" style={{ height: HEADER_HEIGHT }}>
              {hours.map((hour) => (
                <div
                  key={hour}
                  className="flex-1 text-[11px] text-text-muted font-mono border-l border-border-subtle/50 pl-1 flex items-center"
                >
                  {hour}:00
                </div>
              ))}
            </div>

            {/* Tracks */}
            {appTracks.map((track) => {
              const color = getAppColor(track.appName, track.category);
              return (
                <div
                  key={track.appName}
                  className="relative border-t border-border-subtle/30"
                  style={{ height: TRACK_HEIGHT }}
                >
                  {/* Hour grid lines */}
                  <div className="absolute inset-0 flex pointer-events-none">
                    {hours.map((hour) => (
                      <div
                        key={hour}
                        className="flex-1 border-l border-border-subtle/20"
                      />
                    ))}
                  </div>

                  {/* Activity blocks */}
                  {track.blocks.map((block, idx) => {
                    const left = getPosition(block.startTime);
                    const width = getWidth(block.startTime, block.endTime);

                    if (left > 100 || left + width < 0) return null;

                    const durationMin = Math.round((block.endTime.getTime() - block.startTime.getTime()) / 60000);

                    return (
                      <motion.div
                        key={`${track.appName}-${idx}`}
                        initial={{ opacity: 0, scaleX: 0 }}
                        animate={{ opacity: 1, scaleX: 1 }}
                        transition={{ duration: 0.3, delay: idx * 0.02 }}
                        className="absolute top-1 bottom-1 rounded-md cursor-pointer
                                   hover:brightness-110 transition-all group"
                        style={{
                          left: `${left}%`,
                          width: `${width}%`,
                          minWidth: '8px',
                          backgroundColor: `${color}40`,
                          borderLeft: `3px solid ${color}`,
                          boxShadow: `inset 0 0 0 1px ${color}30`,
                        }}
                      >
                        {/* Tooltip on hover */}
                        <div className="absolute bottom-full left-0 mb-1 hidden group-hover:block z-50">
                          <div className="bg-bg-primary border border-border-subtle rounded px-2 py-1 text-[10px] whitespace-nowrap shadow-lg">
                            <div className="font-medium" style={{ color }}>{track.appName}</div>
                            <div className="text-text-muted">
                              {block.startTime.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                              {' - '}
                              {block.endTime.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                            </div>
                            <div className="text-text-muted">{durationMin} мин</div>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              );
            })}

            {/* Current time indicator */}
            {currentPosition >= 0 && currentPosition <= 100 && (
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-30 pointer-events-none"
                style={{ left: `${currentPosition}%` }}
              >
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-red-500 rounded-full shadow-[0_0_8px_rgba(239,68,68,0.6)]" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary footer */}
      {appTracks.length > 0 && (
        <div className="flex items-center justify-between mt-3 pt-2 border-t border-border-subtle text-[10px] text-text-muted">
          <span>{appTracks.length} приложений отслеживается</span>
          <div className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
            <span>Сейчас</span>
          </div>
        </div>
      )}

      {appTracks.length === 0 && (
        <div className="text-center py-8 text-text-muted text-sm">
          Нет данных активности за сегодня
        </div>
      )}
    </motion.div>
  );
}

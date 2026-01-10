import { motion } from 'framer-motion';
import { useRef, useEffect, useMemo } from 'react';
import { Bot, Clock } from 'lucide-react';

interface TimelineEvent {
  id: string;
  type: 'app' | 'agent';
  name: string;
  startTime: string; // ISO string
  endTime?: string;
  category?: string;
  color?: string;
}

interface GroupedEvent {
  id: string;
  name: string;
  startTime: string;
  endTime: string;
  category?: string;
  eventCount: number;
}

interface AppTrack {
  appName: string;
  category: string;
  events: GroupedEvent[];
  totalEvents: number;
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
  other: '#6b7280',
};

// Generate consistent color for app name
const getAppColor = (appName: string, category?: string): string => {
  if (category && categoryColors[category]) {
    return categoryColors[category];
  }
  // Generate color based on app name hash
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
  maxTracks = 5,
}: LiveTimelineProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const hours = Array.from({ length: endHour - startHour + 1 }, (_, i) => startHour + i);
  const totalMinutes = (endHour - startHour + 1) * 60;

  // Group events by app and create tracks
  const appTracks = useMemo(() => {
    const appEvents = events.filter(e => e.type === 'app');
    if (appEvents.length === 0) return [];

    // Group by app name
    const appGroups: Record<string, TimelineEvent[]> = {};
    appEvents.forEach(event => {
      const key = event.name;
      if (!appGroups[key]) appGroups[key] = [];
      appGroups[key].push(event);
    });

    // Create tracks for each app
    const tracks: AppTrack[] = Object.entries(appGroups).map(([appName, events]) => {
      // Sort events chronologically
      const sorted = [...events].sort((a, b) =>
        new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
      );

      // Group consecutive events
      const groups: GroupedEvent[] = [];
      let currentGroup: GroupedEvent | null = null;

      sorted.forEach((event) => {
        const eventTime = new Date(event.startTime);

        if (currentGroup) {
          const groupEnd = new Date(currentGroup.endTime);
          const timeDiff = (eventTime.getTime() - groupEnd.getTime()) / 60000;

          // If less than 3 minutes gap, extend the group
          if (timeDiff < 3) {
            currentGroup.endTime = new Date(eventTime.getTime() + 60000).toISOString();
            currentGroup.eventCount++;
            return;
          }
        }

        if (currentGroup) {
          groups.push(currentGroup);
        }

        currentGroup = {
          id: event.id,
          name: event.name,
          startTime: event.startTime,
          endTime: new Date(eventTime.getTime() + 60000).toISOString(),
          category: event.category,
          eventCount: 1,
        };
      });

      if (currentGroup) {
        groups.push(currentGroup);
      }

      return {
        appName,
        category: events[0]?.category || 'other',
        events: groups,
        totalEvents: events.length,
      };
    });

    // Sort by total events and take top N
    return tracks
      .sort((a, b) => b.totalEvents - a.totalEvents)
      .slice(0, maxTracks);
  }, [events, maxTracks]);

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
    return Math.max(0, (minutes / totalMinutes) * 100);
  };

  const getEventWidth = (startTime: string, endTime: string) => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationMinutes = Math.max(1, (end.getTime() - start.getTime()) / 60000);
    return Math.max((durationMinutes / totalMinutes) * 100, 0.5);
  };

  // Current time indicator
  const now = new Date();
  const currentPosition = ((now.getHours() - startHour) * 60 + now.getMinutes()) / totalMinutes * 100;

  // Calculate height based on number of tracks
  const trackHeight = 20;
  const headerHeight = 24;
  const agentTrackHeight = 24;
  const contentHeight = headerHeight + (appTracks.length * trackHeight) + agentTrackHeight + 8;

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
        <div className="relative min-w-[800px]" style={{ height: `${contentHeight}px` }}>
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
                className="absolute top-0 bottom-0 border-l border-border-subtle/30"
                style={{ left: `${((hour - startHour) / (endHour - startHour + 1)) * 100}%` }}
              />
            ))}
          </div>

          {/* App tracks - each app on its own row */}
          {appTracks.map((track, trackIndex) => {
            const color = getAppColor(track.appName, track.category);
            const topOffset = headerHeight + (trackIndex * trackHeight);

            return (
              <div
                key={track.appName}
                className="absolute left-0 right-0"
                style={{ top: `${topOffset}px`, height: `${trackHeight}px` }}
              >
                {/* App label on the left (outside scroll area would be better, but for now) */}
                <div
                  className="absolute left-0 top-0 h-full flex items-center z-10 pointer-events-none"
                  style={{ width: '70px' }}
                >
                  <span
                    className="text-[9px] font-medium truncate px-1 py-0.5 rounded bg-bg-primary/80"
                    style={{ color }}
                    title={track.appName}
                  >
                    {track.appName.length > 10 ? track.appName.slice(0, 10) + '...' : track.appName}
                  </span>
                </div>

                {/* Events for this app */}
                {track.events.map((event) => {
                  const position = getEventPosition(event.startTime);
                  const width = getEventWidth(event.startTime, event.endTime);

                  if (position > 100 || position + width < 0) return null;

                  return (
                    <motion.div
                      key={`${event.id}-${event.startTime}`}
                      initial={{ opacity: 0, scaleX: 0 }}
                      animate={{ opacity: 1, scaleX: 1 }}
                      className="absolute top-1 h-4 rounded cursor-pointer hover:brightness-125 transition-all"
                      style={{
                        left: `${position}%`,
                        width: `${Math.max(width, 0.3)}%`,
                        backgroundColor: `${color}60`,
                        borderLeft: `2px solid ${color}`,
                        minWidth: '4px',
                      }}
                      title={`${event.name} (${event.eventCount} событий)`}
                    />
                  );
                })}
              </div>
            );
          })}

          {/* Agents track - at the bottom */}
          <div
            className="absolute left-0 right-0"
            style={{ top: `${headerHeight + (appTracks.length * trackHeight)}px`, height: `${agentTrackHeight}px` }}
          >
            {events
              .filter((e) => e.type === 'agent')
              .map((event) => (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute top-1 w-5 h-5 rounded-lg bg-hud-cyan/20 border border-hud-cyan/40
                             flex items-center justify-center cursor-pointer hover:shadow-hud-sm
                             transition-shadow"
                  style={{
                    left: `${getEventPosition(event.startTime)}%`,
                    transform: 'translateX(-50%)',
                  }}
                  title={event.name}
                >
                  <Bot className="w-3 h-3 text-hud-cyan" />
                </motion.div>
              ))}
          </div>

          {/* Current time indicator */}
          {currentPosition >= 0 && currentPosition <= 100 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="absolute top-6 bottom-0 w-0.5 bg-status-error z-20"
              style={{ left: `${currentPosition}%` }}
            >
              <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-status-error rounded-full
                              shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
            </motion.div>
          )}
        </div>
      </div>

      {/* Legend - show app colors */}
      <div className="flex items-center gap-3 mt-2 pt-2 border-t border-border-subtle overflow-x-auto">
        {appTracks.slice(0, 4).map((track) => {
          const color = getAppColor(track.appName, track.category);
          return (
            <div key={track.appName} className="flex items-center gap-1 flex-shrink-0">
              <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: color }} />
              <span className="text-[10px] text-text-muted truncate max-w-[60px]">{track.appName}</span>
            </div>
          );
        })}
        {appTracks.length > 4 && (
          <span className="text-[10px] text-text-muted">+{appTracks.length - 4}</span>
        )}
        <div className="flex items-center gap-1 ml-auto flex-shrink-0">
          <div className="w-1.5 h-1.5 bg-status-error rounded-full" />
          <span className="text-[10px] text-text-muted">Now</span>
        </div>
      </div>
    </motion.div>
  );
}

import { motion } from 'framer-motion';
import { Monitor, FileText, Globe, Code, MessageSquare } from 'lucide-react';
import { formatRelativeTime, truncate } from '../../lib/utils';
import type { Event } from '../../lib/api';

interface TimelineProps {
  events?: Event[];
  loading?: boolean;
}

const categoryConfig: Record<string, { icon: typeof Monitor; color: string; bgColor: string }> = {
  coding: {
    icon: Code,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
  },
  browsing: {
    icon: Globe,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
  },
  writing: {
    icon: FileText,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
  },
  communication: {
    icon: MessageSquare,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
  },
  default: {
    icon: Monitor,
    color: 'text-text-secondary',
    bgColor: 'bg-white/[0.05]',
  },
};

export function Timeline({ events, loading }: TimelineProps) {
  if (loading) {
    return (
      <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent h-full">
        <div className="h-6 w-40 skeleton mb-6" />
        <div className="space-y-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="flex items-start gap-3 p-3">
              <div className="w-8 h-8 rounded-lg skeleton" />
              <div className="flex-1">
                <div className="h-4 w-32 skeleton mb-2" />
                <div className="h-3 w-20 skeleton" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent h-full flex flex-col">
      <h3 className="text-lg font-semibold text-text-primary tracking-tight mb-4">
        Последняя активность
      </h3>

      <div className="flex-1 overflow-y-auto -mx-3 px-3 space-y-1 scrollbar-hide">
        {events && events.length > 0 ? (
          events.slice(0, 15).map((event, i) => {
            const config = categoryConfig[event.category || 'default'] || categoryConfig.default;
            const Icon = config.icon;

            return (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03, duration: 0.2 }}
                className="flex items-start gap-3 p-3 rounded-lg hover:bg-white/[0.03] transition-colors cursor-default"
              >
                <div className={`w-8 h-8 rounded-lg ${config.bgColor} flex items-center justify-center shrink-0`}>
                  <Icon className={`w-4 h-4 ${config.color}`} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-text-primary truncate">
                      {event.app_name || 'Приложение'}
                    </span>
                    <span className="text-xs text-text-muted hidden sm:inline">
                      {truncate(event.window_title || '', 30)}
                    </span>
                  </div>
                  <span className="text-xs text-text-tertiary">
                    {formatRelativeTime(event.timestamp)}
                  </span>
                </div>
              </motion.div>
            );
          })
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center py-8">
              <Monitor className="w-10 h-10 text-text-muted mx-auto mb-3" />
              <p className="text-sm text-text-tertiary">Нет активности</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

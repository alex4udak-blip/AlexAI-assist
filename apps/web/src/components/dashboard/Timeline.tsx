import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Monitor, FileText, Globe, Code, MessageSquare, ChevronDown, ExternalLink } from 'lucide-react';
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

function extractDomain(url: string | null): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace('www.', '');
  } catch {
    return null;
  }
}

export function Timeline({ events, loading }: TimelineProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
            const isExpanded = expandedId === event.id;
            const hasDetails = event.window_title || event.url;
            const domain = extractDomain(event.url);

            return (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03, duration: 0.2 }}
                className="rounded-lg hover:bg-white/[0.03] transition-colors"
              >
                <div
                  className={`flex items-start gap-3 p-3 ${hasDetails ? 'cursor-pointer' : 'cursor-default'}`}
                  onClick={() => hasDetails && setExpandedId(isExpanded ? null : event.id)}
                >
                  <div className={`w-8 h-8 rounded-lg ${config.bgColor} flex items-center justify-center shrink-0`}>
                    <Icon className={`w-4 h-4 ${config.color}`} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-text-primary truncate">
                        {event.app_name || 'Приложение'}
                      </span>
                      {domain && (
                        <span className="text-xs text-purple-400/80 bg-purple-500/10 px-1.5 py-0.5 rounded">
                          {domain}
                        </span>
                      )}
                      {hasDetails && (
                        <ChevronDown
                          className={`w-3 h-3 text-text-muted transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        />
                      )}
                    </div>
                    {event.window_title && !isExpanded && (
                      <p className="text-xs text-text-muted truncate mt-0.5">
                        {truncate(event.window_title, 50)}
                      </p>
                    )}
                    <span className="text-xs text-text-tertiary">
                      {formatRelativeTime(event.timestamp)}
                    </span>
                  </div>
                </div>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="overflow-hidden"
                    >
                      <div className="px-3 pb-3 pl-14 space-y-2">
                        {event.window_title && (
                          <div>
                            <span className="text-xs text-text-tertiary">Заголовок:</span>
                            <p className="text-sm text-text-secondary">{event.window_title}</p>
                          </div>
                        )}
                        {event.url && (
                          <div>
                            <span className="text-xs text-text-tertiary">URL:</span>
                            <a
                              href={event.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-sm text-purple-400 hover:text-purple-300 transition-colors break-all"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {truncate(event.url, 60)}
                              <ExternalLink className="w-3 h-3 shrink-0" />
                            </a>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
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

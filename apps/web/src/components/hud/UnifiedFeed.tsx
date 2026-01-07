import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot, Monitor, Lightbulb, CheckCircle, XCircle, AlertCircle,
  TrendingUp, TrendingDown, Sparkles, RefreshCw
} from 'lucide-react';

type FeedItemType = 'agent' | 'activity' | 'insight';

interface FeedItem {
  id: string;
  type: FeedItemType;
  title: string;
  description: string;
  timestamp: string;
  status?: 'success' | 'error' | 'warning' | 'info';
  icon?: 'bot' | 'monitor' | 'lightbulb' | 'trending-up' | 'trending-down' | 'sparkles';
  metadata?: Record<string, string | number>;
}

interface UnifiedFeedProps {
  items: FeedItem[];
  onRefresh?: () => Promise<void>;
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoading?: boolean;
}

const iconMap = {
  bot: Bot,
  monitor: Monitor,
  lightbulb: Lightbulb,
  'trending-up': TrendingUp,
  'trending-down': TrendingDown,
  sparkles: Sparkles,
};

const statusConfig = {
  success: {
    icon: CheckCircle,
    color: 'text-status-success',
    bg: 'bg-status-success/10',
    border: 'border-status-success/20',
  },
  error: {
    icon: XCircle,
    color: 'text-status-error',
    bg: 'bg-status-error/10',
    border: 'border-status-error/20',
  },
  warning: {
    icon: AlertCircle,
    color: 'text-status-warning',
    bg: 'bg-status-warning/10',
    border: 'border-status-warning/20',
  },
  info: {
    icon: Lightbulb,
    color: 'text-hud-cyan',
    bg: 'bg-hud-cyan/10',
    border: 'border-hud-cyan/20',
  },
};

const typeLabels: Record<FeedItemType, string> = {
  agent: 'Агент',
  activity: 'Активность',
  insight: 'AI Инсайт',
};

export function UnifiedFeed({
  items,
  onRefresh,
  onLoadMore,
  hasMore = false,
  isLoading = false,
}: UnifiedFeedProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [filter, setFilter] = useState<FeedItemType | 'all'>('all');

  const handleRefresh = useCallback(async () => {
    if (!onRefresh || isRefreshing) return;
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
    }
  }, [onRefresh, isRefreshing]);

  const filteredItems = filter === 'all'
    ? items
    : items.filter(item => item.type === filter);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (minutes < 1) return 'Сейчас';
    if (minutes < 60) return `${minutes}м назад`;
    if (hours < 24) return `${hours}ч назад`;
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header with filter */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
        <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono">
          Live Feed
        </h3>
        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="p-2 rounded-lg text-text-muted hover:text-text-primary
                         hover:bg-white/5 transition-colors touch-manipulation"
              style={{ minWidth: '44px', minHeight: '44px' }}
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 px-4 py-2 overflow-x-auto scrollbar-hide">
        {(['all', 'agent', 'activity', 'insight'] as const).map((type) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap
                       transition-colors touch-manipulation
                       ${filter === type
                         ? 'bg-hud-cyan/20 text-hud-cyan'
                         : 'bg-white/5 text-text-muted'
                       }`}
            style={{ minHeight: '32px' }}
          >
            {type === 'all' ? 'Все' : typeLabels[type]}
          </button>
        ))}
      </div>

      {/* Feed list */}
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3">
        <AnimatePresence mode="popLayout">
          {filteredItems.map((item, index) => {
            const config = item.status ? statusConfig[item.status] : statusConfig.info;
            const StatusIcon = config.icon;
            const ItemIcon = item.icon ? iconMap[item.icon] : Monitor;

            return (
              <motion.div
                key={item.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: index * 0.02 }}
                className={`p-4 rounded-xl border ${config.bg} ${config.border}`}
              >
                <div className="flex items-start gap-3">
                  {/* Icon */}
                  <div className={`w-10 h-10 rounded-lg ${config.bg} flex items-center justify-center
                                  flex-shrink-0`}>
                    <ItemIcon className={`w-5 h-5 ${config.color}`} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono text-text-muted uppercase">
                        {typeLabels[item.type]}
                      </span>
                      <StatusIcon className={`w-3 h-3 ${config.color}`} />
                    </div>
                    <h4 className="text-sm font-medium text-text-primary">
                      {item.title}
                    </h4>
                    <p className="text-xs text-text-muted mt-0.5 line-clamp-2">
                      {item.description}
                    </p>

                    {/* Metadata */}
                    {item.metadata && Object.keys(item.metadata).length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {Object.entries(item.metadata).map(([key, value]) => (
                          <span
                            key={key}
                            className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-text-muted"
                          >
                            {key}: <span className="text-hud-cyan">{value}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Time */}
                  <span className="text-[10px] text-text-muted font-mono flex-shrink-0">
                    {formatTime(item.timestamp)}
                  </span>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Empty state */}
        {filteredItems.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Lightbulb className="w-8 h-8 text-text-muted mb-2" />
            <p className="text-sm text-text-muted">Нет событий</p>
          </div>
        )}

        {/* Load more */}
        {hasMore && onLoadMore && (
          <button
            onClick={onLoadMore}
            disabled={isLoading}
            className="w-full py-3 text-center text-sm text-text-muted
                       hover:text-text-primary transition-colors touch-manipulation"
            style={{ minHeight: '44px' }}
          >
            {isLoading ? 'Загрузка...' : 'Загрузить ещё'}
          </button>
        )}
      </div>
    </div>
  );
}

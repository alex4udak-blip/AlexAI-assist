import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { CategoryBreakdown } from '../components/analytics/CategoryBreakdown';
import { ProductivityScore } from '../components/analytics/ProductivityScore';
import { AppUsage } from '../components/analytics/AppUsage';
import { TrendChart } from '../components/analytics/TrendChart';
import {
  useCategories,
  useProductivity,
  useAppUsage,
  useTrends,
} from '../hooks/useAnalytics';
import { useEventsCreated } from '../hooks/useWebSocketSync';
import { useWebSocket } from '../hooks/useWebSocket';

type Period = '7' | '14' | '30';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function Analytics() {
  const [period, setPeriod] = useState<Period>('7');

  // Connect to WebSocket for real-time updates
  useWebSocket();

  const { data: categories, loading: categoriesLoading, refetch: refetchCategories } = useCategories({
    days: parseInt(period),
  });
  const { data: productivity, loading: productivityLoading, refetch: refetchProductivity } = useProductivity({
    days: parseInt(period),
  });
  const { data: appUsage, loading: appUsageLoading, refetch: refetchAppUsage } = useAppUsage({
    days: parseInt(period),
  });
  const { data: trends, loading: trendsLoading, refetch: refetchTrends } = useTrends({
    days: parseInt(period),
  });

  // Handle real-time event updates
  const handleEventsCreated = useCallback(() => {
    refetchCategories();
    refetchProductivity();
    refetchAppUsage();
    refetchTrends();
  }, [refetchCategories, refetchProductivity, refetchAppUsage, refetchTrends]);

  // Subscribe to real-time events
  useEventsCreated(handleEventsCreated);

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6 max-w-7xl mx-auto"
    >
      {/* Period selector */}
      <motion.div variants={item} className="flex justify-end">
        <div className="flex gap-1 p-1 rounded-lg bg-white/[0.03]">
          {(['7', '14', '30'] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-150
                         ${period === p
                           ? 'bg-white/[0.08] text-text-primary'
                           : 'text-text-tertiary hover:text-text-secondary hover:bg-white/[0.03]'
                         }`}
            >
              {p === '7' ? '7 дней' : p === '14' ? '14 дней' : '30 дней'}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Productivity + Categories */}
      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ProductivityScore data={productivity ?? undefined} loading={productivityLoading} />
        <CategoryBreakdown data={categories ?? undefined} loading={categoriesLoading} />
      </motion.div>

      {/* Trend chart */}
      <motion.div variants={item}>
        <TrendChart data={trends ?? undefined} loading={trendsLoading} />
      </motion.div>

      {/* App usage */}
      <motion.div variants={item}>
        <AppUsage data={appUsage ?? undefined} loading={appUsageLoading} />
      </motion.div>
    </motion.div>
  );
}

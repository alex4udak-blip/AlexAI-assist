import { useState } from 'react';
import { Select } from '../components/ui/Select';
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

const periodOptions = [
  { value: '7', label: 'Last 7 days' },
  { value: '14', label: 'Last 14 days' },
  { value: '30', label: 'Last 30 days' },
];

export default function Analytics() {
  const [period, setPeriod] = useState('7');

  const { data: categories, loading: categoriesLoading } = useCategories({
    days: parseInt(period),
  });
  const { data: productivity, loading: productivityLoading } = useProductivity();
  const { data: appUsage, loading: appUsageLoading } = useAppUsage({
    days: parseInt(period),
  });
  const { data: trends, loading: trendsLoading } = useTrends({
    days: parseInt(period),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Analytics</h1>
          <p className="text-text-tertiary mt-1">
            Insights into your activity patterns
          </p>
        </div>
        <Select
          options={periodOptions}
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="w-40"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ProductivityScore data={productivity ?? undefined} loading={productivityLoading} />
        <CategoryBreakdown data={categories ?? undefined} loading={categoriesLoading} />
      </div>

      <TrendChart data={trends ?? undefined} loading={trendsLoading} />

      <AppUsage data={appUsage ?? undefined} loading={appUsageLoading} />
    </div>
  );
}

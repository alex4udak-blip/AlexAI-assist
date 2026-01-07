import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface ActivityChartProps {
  data?: { hour: number; count: number }[];
  loading?: boolean;
}

type Period = 'day' | 'week' | 'month';

export function ActivityChart({ data, loading }: ActivityChartProps) {
  const [period, setPeriod] = useState<Period>('day');

  const chartData = data || Array.from({ length: 24 }, (_, i) => ({
    hour: i,
    count: 0,
  }));

  const formattedData = chartData.map((item) => ({
    ...item,
    label: `${item.hour.toString().padStart(2, '0')}:00`,
  }));

  if (loading) {
    return (
      <div className="p-6 rounded-2xl border border-border-subtle bg-surface-primary">
        <div className="flex items-center justify-between mb-6">
          <div className="h-6 w-32 skeleton" />
          <div className="h-8 w-48 skeleton" />
        </div>
        <div className="h-64 skeleton rounded-xl" />
      </div>
    );
  }

  return (
    <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-text-primary tracking-tight">
          Активность
        </h3>
        <div className="flex gap-1 p-1 rounded-lg bg-white/[0.03]">
          {(['day', 'week', 'month'] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-150
                         ${period === p
                           ? 'bg-white/[0.08] text-text-primary'
                           : 'text-text-tertiary hover:text-text-secondary hover:bg-white/[0.03]'
                         }`}
            >
              {p === 'day' ? 'День' : p === 'week' ? 'Неделя' : 'Месяц'}
            </button>
          ))}
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={formattedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="activityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8B5CF6" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#8B5CF6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="label"
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 12 }}
              interval="preserveStartEnd"
              tickMargin={10}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 12 }}
              width={40}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#161616',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '12px',
                color: '#ffffff',
                fontSize: '13px',
                padding: '8px 12px',
              }}
              itemStyle={{ color: '#8B5CF6' }}
              labelStyle={{ color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}
              cursor={{ stroke: 'rgba(255,255,255,0.1)' }}
            />
            <Area
              type="monotone"
              dataKey="count"
              stroke="#8B5CF6"
              strokeWidth={2}
              fill="url(#activityGradient)"
              animationDuration={500}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

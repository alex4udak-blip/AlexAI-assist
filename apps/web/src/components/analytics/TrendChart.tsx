import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp } from 'lucide-react';
import { formatDate } from '../../lib/utils';

interface TrendChartProps {
  data?: { date: string; count: number }[];
  loading?: boolean;
}

export function TrendChart({ data, loading }: TrendChartProps) {
  if (loading) {
    return (
      <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl skeleton" />
          <div className="h-6 w-40 skeleton" />
        </div>
        <div className="h-64 skeleton rounded-xl" />
      </div>
    );
  }

  const chartData = (data || []).map((item) => ({
    ...item,
    label: formatDate(item.date),
  }));

  return (
    <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-blue-500/5
                        flex items-center justify-center">
          <TrendingUp className="w-5 h-5 text-blue-400" />
        </div>
        <h3 className="text-lg font-semibold text-text-primary tracking-tight">
          Тренды активности
        </h3>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6366F1" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#6366F1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="label"
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 12 }}
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
              itemStyle={{ color: '#6366F1' }}
              labelStyle={{ color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}
              cursor={{ stroke: 'rgba(255,255,255,0.1)' }}
            />
            <Area
              type="monotone"
              dataKey="count"
              stroke="#6366F1"
              strokeWidth={2}
              fill="url(#trendGradient)"
              dot={{ fill: '#6366F1', strokeWidth: 0, r: 3 }}
              activeDot={{
                r: 5,
                fill: '#818CF8',
                stroke: '#6366F1',
                strokeWidth: 2,
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

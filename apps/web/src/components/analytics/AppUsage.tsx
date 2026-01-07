import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts';
import { Layers } from 'lucide-react';

interface AppUsageProps {
  data?: { app_name: string; event_count: number }[];
  loading?: boolean;
}

const BAR_COLORS = [
  '#8B5CF6',
  '#7C3AED',
  '#6D28D9',
  '#5B21B6',
  '#4C1D95',
  '#6366F1',
  '#4F46E5',
  '#4338CA',
  '#3730A3',
  '#312E81',
];

export function AppUsage({ data, loading }: AppUsageProps) {
  if (loading) {
    return (
      <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl skeleton" />
          <div className="h-6 w-40 skeleton" />
        </div>
        <div className="h-80 skeleton rounded-xl" />
      </div>
    );
  }

  const chartData = (data || []).slice(0, 10);

  return (
    <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-500/5
                        flex items-center justify-center">
          <Layers className="w-5 h-5 text-amber-400" />
        </div>
        <h3 className="text-lg font-semibold text-text-primary tracking-tight">
          Топ приложений
        </h3>
      </div>

      {chartData.length > 0 ? (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
            >
              <XAxis
                type="number"
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 12 }}
              />
              <YAxis
                type="category"
                dataKey="app_name"
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                width={120}
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
                formatter={(value: number) => [`${value} событий`, '']}
                labelStyle={{ color: 'rgba(255,255,255,0.7)', marginBottom: '4px' }}
                cursor={{ fill: 'rgba(255,255,255,0.03)' }}
              />
              <Bar
                dataKey="event_count"
                radius={[0, 6, 6, 0]}
                maxBarSize={24}
              >
                {chartData.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={BAR_COLORS[index % BAR_COLORS.length]}
                    style={{
                      filter: `drop-shadow(0 0 6px ${BAR_COLORS[index % BAR_COLORS.length]}40)`,
                    }}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="flex items-center justify-center h-64">
          <p className="text-sm text-text-muted">Нет данных о приложениях</p>
        </div>
      )}
    </div>
  );
}

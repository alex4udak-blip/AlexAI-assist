import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { PieChart as PieChartIcon } from 'lucide-react';

interface CategoryBreakdownProps {
  data?: { category: string; count: number }[];
  loading?: boolean;
}

const COLORS = [
  { fill: '#8B5CF6', glow: 'rgba(139, 92, 246, 0.3)' },
  { fill: '#6366F1', glow: 'rgba(99, 102, 241, 0.3)' },
  { fill: '#3B82F6', glow: 'rgba(59, 130, 246, 0.3)' },
  { fill: '#10B981', glow: 'rgba(16, 185, 129, 0.3)' },
  { fill: '#F59E0B', glow: 'rgba(245, 158, 11, 0.3)' },
  { fill: '#EF4444', glow: 'rgba(239, 68, 68, 0.3)' },
];

const categoryLabels: Record<string, string> = {
  coding: 'Код',
  browsing: 'Браузер',
  writing: 'Документы',
  communication: 'Общение',
  design: 'Дизайн',
  other: 'Другое',
};

export function CategoryBreakdown({ data, loading }: CategoryBreakdownProps) {
  if (loading) {
    return (
      <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl skeleton" />
          <div className="h-6 w-40 skeleton" />
        </div>
        <div className="flex items-center gap-8">
          <div className="w-40 h-40 rounded-full skeleton" />
          <div className="flex-1 space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-6 skeleton" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const chartData = data || [];
  const total = chartData.reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-violet-500/5
                        flex items-center justify-center">
          <PieChartIcon className="w-5 h-5 text-violet-400" />
        </div>
        <h3 className="text-lg font-semibold text-text-primary tracking-tight">
          По категориям
        </h3>
      </div>

      {chartData.length > 0 ? (
        <div className="flex items-center gap-6">
          {/* Chart */}
          <div className="w-40 h-40 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  paddingAngle={3}
                  dataKey="count"
                >
                  {chartData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length].fill}
                      style={{
                        filter: `drop-shadow(0 0 6px ${COLORS[index % COLORS.length].glow})`,
                      }}
                    />
                  ))}
                </Pie>
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
                  labelFormatter={(label) => categoryLabels[label] || label}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="flex-1 space-y-2">
            {chartData.map((item, index) => {
              const percentage = total > 0 ? ((item.count / total) * 100).toFixed(0) : 0;
              return (
                <div
                  key={item.category}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/[0.02] transition-colors"
                >
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{
                      backgroundColor: COLORS[index % COLORS.length].fill,
                      boxShadow: `0 0 8px ${COLORS[index % COLORS.length].glow}`,
                    }}
                  />
                  <span className="text-sm text-text-secondary flex-1">
                    {categoryLabels[item.category] || item.category}
                  </span>
                  <span className="text-sm font-medium text-text-primary">
                    {percentage}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center h-40">
          <p className="text-sm text-text-muted">Нет данных</p>
        </div>
      )}
    </div>
  );
}

import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell, CartesianGrid } from 'recharts';
import { Layers } from 'lucide-react';
import { motion } from 'framer-motion';
import { HoloCard, HudHeader, AnimatedGrid, HolographicShimmer } from './SciFiElements';

interface AppUsageProps {
  data?: { app_name: string; event_count: number }[];
  loading?: boolean;
}

const BAR_COLORS = [
  { fill: '#8B5CF6', glow: 'rgba(139, 92, 246, 0.6)' },
  { fill: '#7C3AED', glow: 'rgba(124, 58, 237, 0.6)' },
  { fill: '#6D28D9', glow: 'rgba(109, 40, 217, 0.6)' },
  { fill: '#5B21B6', glow: 'rgba(91, 33, 182, 0.6)' },
  { fill: '#6366F1', glow: 'rgba(99, 102, 241, 0.6)' },
  { fill: '#4F46E5', glow: 'rgba(79, 70, 229, 0.6)' },
  { fill: '#4338CA', glow: 'rgba(67, 56, 202, 0.6)' },
  { fill: '#3730A3', glow: 'rgba(55, 48, 163, 0.6)' },
  { fill: '#06b6d4', glow: 'rgba(6, 182, 212, 0.6)' },
  { fill: '#0891b2', glow: 'rgba(8, 145, 178, 0.6)' },
];

export function AppUsage({ data, loading }: AppUsageProps) {
  if (loading) {
    return (
      <HoloCard glowColor="amber">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl skeleton" />
          <div className="h-6 w-40 skeleton" />
        </div>
        <div className="h-80 skeleton rounded-xl" />
      </HoloCard>
    );
  }

  const chartData = (data || []).slice(0, 10);

  return (
    <HoloCard glowColor="amber">
      <HolographicShimmer />
      <HudHeader
        icon={<Layers className="w-5 h-5 text-amber-400" />}
        title="ТОП ПРИЛОЖЕНИЙ"
        iconColor="amber"
        glowColor="amber"
      />

      {chartData.length > 0 ? (
        <div className="relative h-96">
          {/* Animated background grid */}
          <AnimatedGrid />

          <motion.div
            className="relative h-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
              >
                <defs>
                  {/* Gradient definitions for each bar */}
                  {BAR_COLORS.map((color, index) => (
                    <linearGradient key={`gradient-${index}`} id={`barGradient-${index}`} x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor={color.fill} stopOpacity={0.4} />
                      <stop offset="100%" stopColor={color.fill} stopOpacity={1} />
                    </linearGradient>
                  ))}
                </defs>

                {/* Animated grid */}
                <CartesianGrid
                  stroke="rgba(245, 158, 11, 0.1)"
                  strokeDasharray="3 3"
                  horizontal={false}
                />

                <XAxis
                  type="number"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: 'rgba(245, 158, 11, 0.5)', fontSize: 11, fontFamily: 'monospace' }}
                />
                <YAxis
                  type="category"
                  dataKey="app_name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: 'rgba(245, 158, 11, 0.7)', fontSize: 11, fontFamily: 'monospace' }}
                  width={140}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0a0a0a',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    borderRadius: '12px',
                    color: '#ffffff',
                    fontSize: '13px',
                    padding: '12px 16px',
                    boxShadow: '0 0 20px rgba(245, 158, 11, 0.3)',
                    fontFamily: 'monospace',
                  }}
                  formatter={(value: number) => [`${value} событий`, '']}
                  labelStyle={{ color: 'rgba(245, 158, 11, 0.7)', marginBottom: '4px' }}
                  cursor={{
                    fill: 'rgba(245, 158, 11, 0.05)',
                    stroke: 'rgba(245, 158, 11, 0.3)',
                    strokeWidth: 1,
                  }}
                />
                <Bar
                  dataKey="event_count"
                  radius={[0, 8, 8, 0]}
                  maxBarSize={28}
                  animationDuration={1500}
                  animationEasing="ease-out"
                >
                  {chartData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={`url(#barGradient-${index % BAR_COLORS.length})`}
                      style={{
                        filter: `drop-shadow(0 0 8px ${BAR_COLORS[index % BAR_COLORS.length].glow})
                                 drop-shadow(0 0 12px ${BAR_COLORS[index % BAR_COLORS.length].glow})`,
                      }}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Corner markers for HUD effect */}
          <div className="absolute top-0 left-0 w-8 h-8 border-l-2 border-t-2 border-amber-500/40" />
          <div className="absolute top-0 right-0 w-8 h-8 border-r-2 border-t-2 border-amber-500/40" />
          <div className="absolute bottom-0 left-0 w-8 h-8 border-l-2 border-b-2 border-amber-500/40" />
          <div className="absolute bottom-0 right-0 w-8 h-8 border-r-2 border-b-2 border-amber-500/40" />

          {/* Side indicator bars */}
          <motion.div
            className="absolute left-0 top-1/2 w-1 h-12 -translate-y-1/2 bg-gradient-to-b from-transparent via-amber-400/60 to-transparent"
            animate={{
              opacity: [0.4, 1, 0.4],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
          <motion.div
            className="absolute right-0 top-1/2 w-1 h-12 -translate-y-1/2 bg-gradient-to-b from-transparent via-amber-400/60 to-transparent"
            animate={{
              opacity: [0.4, 1, 0.4],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: 1,
            }}
          />
        </div>
      ) : (
        <div className="flex items-center justify-center h-64">
          <p className="text-sm text-text-muted font-mono">НЕТ ДАННЫХ О ПРИЛОЖЕНИЯХ</p>
        </div>
      )}
    </HoloCard>
  );
}

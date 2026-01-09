import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { PieChart as PieChartIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import { HoloCard, HudHeader, HolographicShimmer } from './SciFiElements';

interface CategoryBreakdownProps {
  data?: { category: string; count: number }[];
  loading?: boolean;
}

const COLORS = [
  { fill: '#8B5CF6', glow: 'rgba(139, 92, 246, 0.6)' },
  { fill: '#6366F1', glow: 'rgba(99, 102, 241, 0.6)' },
  { fill: '#3B82F6', glow: 'rgba(59, 130, 246, 0.6)' },
  { fill: '#10B981', glow: 'rgba(16, 185, 129, 0.6)' },
  { fill: '#F59E0B', glow: 'rgba(245, 158, 11, 0.6)' },
  { fill: '#EF4444', glow: 'rgba(239, 68, 68, 0.6)' },
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
      <HoloCard glowColor="violet">
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
      </HoloCard>
    );
  }

  const chartData = data || [];
  const total = chartData.reduce((sum, item) => sum + item.count, 0);

  return (
    <HoloCard glowColor="violet">
      <HolographicShimmer />
      <HudHeader
        icon={<PieChartIcon className="w-5 h-5 text-violet-400" />}
        title="ПО КАТЕГОРИЯМ"
        iconColor="violet"
        glowColor="purple"
      />

      {chartData.length > 0 ? (
        <div className="flex items-center gap-6">
          {/* Chart - Enhanced with holographic glow */}
          <div className="relative w-48 h-48 shrink-0">
            {/* Outer rotating ring */}
            <motion.div
              className="absolute inset-0 rounded-full border border-violet-500/20"
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            />

            {/* Pulsing glow */}
            <motion.div
              className="absolute inset-0 rounded-full"
              style={{
                background: 'radial-gradient(circle, rgba(139, 92, 246, 0.2) 0%, transparent 70%)',
              }}
              animate={{
                scale: [1, 1.1, 1],
                opacity: [0.3, 0.6, 0.3],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />

            <motion.div
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 100, damping: 15 }}
            >
              <ResponsiveContainer width={192} height={192}>
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="count"
                  >
                    {chartData.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length].fill}
                        style={{
                          filter: `drop-shadow(0 0 10px ${COLORS[index % COLORS.length].glow})
                                   drop-shadow(0 0 15px ${COLORS[index % COLORS.length].glow})`,
                        }}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0a0a0a',
                      border: '1px solid rgba(139, 92, 246, 0.3)',
                      borderRadius: '12px',
                      color: '#ffffff',
                      fontSize: '13px',
                      padding: '8px 12px',
                      boxShadow: '0 0 20px rgba(139, 92, 246, 0.3)',
                    }}
                    formatter={(value: number) => [`${value} событий`, '']}
                    labelFormatter={(label) => categoryLabels[label] || label}
                  />
                </PieChart>
              </ResponsiveContainer>
            </motion.div>

            {/* Center holographic indicator */}
            <motion.div
              className="absolute inset-0 flex items-center justify-center pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <div className="w-20 h-20 rounded-full border-2 border-violet-500/30 flex items-center justify-center">
                <motion.div
                  className="w-16 h-16 rounded-full bg-gradient-to-br from-violet-500/20 to-transparent"
                  animate={{ rotate: -360 }}
                  transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
                />
              </div>
            </motion.div>
          </div>

          {/* Legend - Enhanced with sci-fi styling */}
          <div className="flex-1 space-y-2">
            {chartData.map((item, index) => {
              const percentage = total > 0 ? ((item.count / total) * 100).toFixed(0) : 0;
              return (
                <motion.div
                  key={item.category}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * index }}
                  className="relative flex items-center gap-3 p-3 rounded-lg
                             bg-gradient-to-r from-white/[0.03] to-transparent
                             border border-white/[0.05]
                             hover:border-white/[0.15] hover:from-white/[0.05]
                             transition-all duration-300 group overflow-hidden"
                >
                  {/* Scan line effect on hover */}
                  <motion.div
                    className="absolute left-0 top-0 w-full h-[1px] bg-gradient-to-r from-transparent via-white/30 to-transparent"
                    initial={{ x: '-100%' }}
                    whileHover={{ x: '100%' }}
                    transition={{ duration: 0.6 }}
                  />

                  <motion.div
                    className="w-3 h-3 rounded-full shrink-0 relative"
                    style={{
                      backgroundColor: COLORS[index % COLORS.length].fill,
                      boxShadow: `0 0 12px ${COLORS[index % COLORS.length].glow}`,
                    }}
                    animate={{
                      boxShadow: [
                        `0 0 8px ${COLORS[index % COLORS.length].glow}`,
                        `0 0 15px ${COLORS[index % COLORS.length].glow}`,
                        `0 0 8px ${COLORS[index % COLORS.length].glow}`,
                      ],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: 'easeInOut',
                      delay: index * 0.2,
                    }}
                  >
                    <motion.div
                      className="absolute inset-0 rounded-full"
                      style={{ backgroundColor: COLORS[index % COLORS.length].fill }}
                      animate={{
                        scale: [1, 1.5, 1],
                        opacity: [0.8, 0, 0.8],
                      }}
                      transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: 'easeInOut',
                        delay: index * 0.2,
                      }}
                    />
                  </motion.div>

                  <span className="text-sm text-text-secondary flex-1 font-mono">
                    {categoryLabels[item.category] || item.category}
                  </span>

                  <motion.span
                    className="text-sm font-bold font-mono"
                    style={{ color: COLORS[index % COLORS.length].fill }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 + index * 0.1 }}
                  >
                    {percentage}%
                  </motion.span>
                </motion.div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center h-40">
          <p className="text-sm text-text-muted font-mono">НЕТ ДАННЫХ</p>
        </div>
      )}
    </HoloCard>
  );
}

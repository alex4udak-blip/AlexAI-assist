import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';
import { formatDate } from '../../lib/utils';
import { HoloCard, HudHeader, AnimatedGrid, HolographicShimmer } from './SciFiElements';

interface TrendChartProps {
  data?: { date: string; count: number }[];
  loading?: boolean;
}

export function TrendChart({ data, loading }: TrendChartProps) {
  if (loading) {
    return (
      <HoloCard glowColor="blue">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl skeleton" />
          <div className="h-6 w-40 skeleton" />
        </div>
        <div className="h-64 skeleton rounded-xl" />
      </HoloCard>
    );
  }

  const chartData = (data || []).map((item) => ({
    ...item,
    label: formatDate(item.date),
  }));

  return (
    <HoloCard glowColor="blue">
      <HolographicShimmer />
      <HudHeader
        icon={<TrendingUp className="w-5 h-5 text-blue-400" />}
        title="ТРЕНДЫ АКТИВНОСТИ"
        iconColor="blue"
        glowColor="blue"
      />

      <div className="relative h-80">
        {/* Animated background grid */}
        <AnimatedGrid />

        <motion.div
          className="relative h-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                {/* Enhanced gradient with multiple stops */}
                <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.6} />
                  <stop offset="50%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>

                {/* Glow filter for the line */}
                <filter id="lineGlow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Animated grid */}
              <CartesianGrid
                stroke="rgba(6, 182, 212, 0.1)"
                strokeDasharray="3 3"
                vertical={false}
              />

              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'rgba(6, 182, 212, 0.5)', fontSize: 11, fontFamily: 'monospace' }}
                tickMargin={10}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'rgba(6, 182, 212, 0.5)', fontSize: 11, fontFamily: 'monospace' }}
                width={40}
              />

              <Tooltip
                contentStyle={{
                  backgroundColor: '#0a0a0a',
                  border: '1px solid rgba(6, 182, 212, 0.3)',
                  borderRadius: '12px',
                  color: '#ffffff',
                  fontSize: '13px',
                  padding: '12px 16px',
                  boxShadow: '0 0 20px rgba(6, 182, 212, 0.3)',
                  fontFamily: 'monospace',
                }}
                itemStyle={{ color: '#06b6d4' }}
                labelStyle={{ color: 'rgba(6, 182, 212, 0.7)', marginBottom: '4px' }}
                cursor={{
                  stroke: 'rgba(6, 182, 212, 0.3)',
                  strokeWidth: 2,
                  strokeDasharray: '5 5',
                }}
              />

              {/* Main area with enhanced glow */}
              <Area
                type="monotone"
                dataKey="count"
                stroke="#06b6d4"
                strokeWidth={3}
                fill="url(#trendGradient)"
                filter="url(#lineGlow)"
                dot={{
                  fill: '#06b6d4',
                  strokeWidth: 2,
                  stroke: '#0a0a0a',
                  r: 4,
                  style: {
                    filter: 'drop-shadow(0 0 6px rgba(6, 182, 212, 0.8))',
                  },
                }}
                activeDot={{
                  r: 7,
                  fill: '#06b6d4',
                  stroke: '#0ea5e9',
                  strokeWidth: 3,
                  style: {
                    filter: 'drop-shadow(0 0 10px rgba(6, 182, 212, 1))',
                  },
                }}
                animationDuration={1500}
                animationEasing="ease-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Corner markers for HUD effect */}
        <div className="absolute top-0 left-0 w-8 h-8 border-l-2 border-t-2 border-cyan-500/40" />
        <div className="absolute top-0 right-0 w-8 h-8 border-r-2 border-t-2 border-cyan-500/40" />
        <div className="absolute bottom-0 left-0 w-8 h-8 border-l-2 border-b-2 border-cyan-500/40" />
        <div className="absolute bottom-0 right-0 w-8 h-8 border-r-2 border-b-2 border-cyan-500/40" />

        {/* Animated scan lines */}
        <motion.div
          className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent"
          animate={{
            opacity: [0.3, 0.8, 0.3],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </div>
    </HoloCard>
  );
}

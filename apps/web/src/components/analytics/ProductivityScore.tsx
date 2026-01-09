import { Target } from 'lucide-react';
import { motion } from 'framer-motion';
import { HoloCard, HudHeader, PulsingIndicator, HolographicShimmer } from './SciFiElements';

interface ProductivityScoreProps {
  data?: {
    score: number;
    productive_events: number;
    total_events: number;
    trend: string;
  };
  loading?: boolean;
}

export function ProductivityScore({ data, loading }: ProductivityScoreProps) {
  if (loading) {
    return (
      <HoloCard glowColor="emerald">
        <div className="flex items-center justify-between mb-6">
          <div className="h-6 w-48 skeleton" />
          <div className="h-6 w-16 skeleton" />
        </div>
        <div className="flex items-center gap-8">
          <div className="w-32 h-32 rounded-full skeleton" />
          <div className="flex-1 space-y-4">
            <div className="h-4 w-full skeleton" />
            <div className="h-4 w-3/4 skeleton" />
          </div>
        </div>
      </HoloCard>
    );
  }

  const score = data?.score ?? 0;

  const getScoreColor = () => {
    if (score >= 70) return { stroke: '#10B981', glow: 'rgba(16, 185, 129, 0.5)', name: 'emerald' };
    if (score >= 40) return { stroke: '#F59E0B', glow: 'rgba(245, 158, 11, 0.5)', name: 'amber' };
    return { stroke: '#EF4444', glow: 'rgba(239, 68, 68, 0.5)', name: 'red' };
  };

  const colors = getScoreColor();
  const circumference = 2 * Math.PI * 44;
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <HoloCard glowColor="emerald">
      <HolographicShimmer />
      <HudHeader
        icon={<Target className="w-5 h-5 text-emerald-400" />}
        title="ПРОДУКТИВНОСТЬ"
        iconColor="emerald"
        glowColor="emerald"
      />

      <div className="flex items-center gap-8">
        {/* Score Ring - Enhanced with holographic effect */}
        <div className="relative w-36 h-36 shrink-0">
          {/* Outer glow ring */}
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{
              background: `radial-gradient(circle, ${colors.glow} 0%, transparent 70%)`,
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

          <svg className="w-36 h-36 transform -rotate-90 relative z-10" viewBox="0 0 100 100">
            {/* Multiple background circles for depth */}
            <circle
              cx="50"
              cy="50"
              r="44"
              stroke="rgba(6, 182, 212, 0.05)"
              strokeWidth="8"
              fill="none"
            />
            <circle
              cx="50"
              cy="50"
              r="44"
              stroke="rgba(255, 255, 255, 0.03)"
              strokeWidth="6"
              fill="none"
            />

            {/* Animated background pulse */}
            <motion.circle
              cx="50"
              cy="50"
              r="44"
              stroke={colors.stroke}
              strokeWidth="2"
              fill="none"
              opacity="0.2"
              initial={{ strokeDasharray: circumference }}
              animate={{
                strokeDashoffset: [0, -circumference],
              }}
              transition={{
                duration: 8,
                repeat: Infinity,
                ease: 'linear',
              }}
            />

            {/* Progress circle with enhanced glow */}
            <motion.circle
              cx="50"
              cy="50"
              r="44"
              stroke={colors.stroke}
              strokeWidth="7"
              fill="none"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              strokeLinecap="round"
              style={{
                filter: `drop-shadow(0 0 12px ${colors.glow}) drop-shadow(0 0 20px ${colors.glow})`,
              }}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: dashOffset }}
              transition={{ duration: 1.5, ease: 'easeOut' }}
            />

            {/* Inner glow circle */}
            <circle
              cx="50"
              cy="50"
              r="38"
              stroke={colors.stroke}
              strokeWidth="0.5"
              fill="none"
              opacity="0.3"
            />
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.span
              className="text-4xl font-bold font-mono"
              style={{ color: colors.stroke }}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.3 }}
            >
              {score}
            </motion.span>
            <span className="text-xs text-text-muted font-mono">ИЗ 100</span>
            <PulsingIndicator color={colors.name} />
          </div>
        </div>

        {/* Stats - Enhanced with holographic effect */}
        <div className="flex-1 space-y-4">
          <motion.div
            className="relative p-4 rounded-xl bg-gradient-to-br from-emerald-500/10 to-transparent
                       border border-emerald-500/20 backdrop-blur-sm overflow-hidden"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-emerald-400/50 to-transparent" />
            <div className="flex justify-between items-center mb-2">
              <div className="flex items-center gap-2">
                <PulsingIndicator color="green" />
                <span className="text-sm text-text-tertiary font-mono">ПРОДУКТИВНЫХ</span>
              </div>
              <motion.span
                className="text-sm font-bold text-emerald-400 font-mono"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
              >
                {data?.productive_events ?? 0}
              </motion.span>
            </div>
            <div className="h-2 bg-black/30 rounded-full overflow-hidden border border-emerald-500/20">
              <motion.div
                className="h-full bg-gradient-to-r from-emerald-500 to-green-400 rounded-full"
                style={{
                  boxShadow: '0 0 10px rgba(16, 185, 129, 0.5)',
                }}
                initial={{ width: 0 }}
                animate={{
                  width: `${data?.total_events ? (data.productive_events / data.total_events) * 100 : 0}%`,
                }}
                transition={{ duration: 1, delay: 0.7 }}
              />
            </div>
          </motion.div>

          <motion.div
            className="relative p-4 rounded-xl bg-gradient-to-br from-cyan-500/10 to-transparent
                       border border-cyan-500/20 backdrop-blur-sm overflow-hidden"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
          >
            <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
            <div className="flex justify-between items-center mb-2">
              <div className="flex items-center gap-2">
                <PulsingIndicator color="cyan" />
                <span className="text-sm text-text-tertiary font-mono">ВСЕГО СОБЫТИЙ</span>
              </div>
              <motion.span
                className="text-sm font-bold text-cyan-400 font-mono"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
              >
                {data?.total_events ?? 0}
              </motion.span>
            </div>
            <div className="h-2 bg-black/30 rounded-full overflow-hidden border border-cyan-500/20">
              <motion.div
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-400 rounded-full w-full"
                style={{
                  boxShadow: '0 0 10px rgba(6, 182, 212, 0.5)',
                }}
                initial={{ width: 0 }}
                animate={{ width: '100%' }}
                transition={{ duration: 1, delay: 0.8 }}
              />
            </div>
          </motion.div>
        </div>
      </div>
    </HoloCard>
  );
}

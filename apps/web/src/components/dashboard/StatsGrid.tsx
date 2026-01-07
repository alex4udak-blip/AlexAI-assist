import { motion } from 'framer-motion';
import { Activity, Bot, Sparkles, Clock } from 'lucide-react';
import { formatNumber } from '../../lib/utils';

interface Stat {
  label: string;
  value: number | string;
  icon: typeof Activity;
  color: string;
  bgColor: string;
}

interface StatsGridProps {
  stats?: {
    totalEvents: number;
    activeAgents: number;
    suggestions: number;
    timeSaved: number;
  };
  loading?: boolean;
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export function StatsGrid({ stats, loading }: StatsGridProps) {
  const items: Stat[] = [
    {
      label: 'Событий сегодня',
      value: stats?.totalEvents ?? 0,
      icon: Activity,
      color: 'text-violet-400',
      bgColor: 'from-violet-500/20 to-violet-500/5',
    },
    {
      label: 'Активных агентов',
      value: stats?.activeAgents ?? 0,
      icon: Bot,
      color: 'text-emerald-400',
      bgColor: 'from-emerald-500/20 to-emerald-500/5',
    },
    {
      label: 'Предложений',
      value: stats?.suggestions ?? 0,
      icon: Sparkles,
      color: 'text-amber-400',
      bgColor: 'from-amber-500/20 to-amber-500/5',
    },
    {
      label: 'Сэкономлено',
      value: stats?.timeSaved ? `${stats.timeSaved}м` : '0м',
      icon: Clock,
      color: 'text-blue-400',
      bgColor: 'from-blue-500/20 to-blue-500/5',
    },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="p-5 rounded-2xl border border-border-subtle bg-surface-primary">
            <div className="w-10 h-10 rounded-xl skeleton mb-4" />
            <div className="h-8 w-20 skeleton mb-2" />
            <div className="h-4 w-24 skeleton" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-2 lg:grid-cols-4 gap-4"
    >
      {items.map((stat) => (
        <motion.div
          key={stat.label}
          variants={item}
          className="group relative p-5 rounded-2xl border border-border-subtle
                     bg-gradient-to-br from-white/[0.03] to-transparent
                     hover:border-border-default transition-all duration-200"
        >
          {/* Glow effect on hover */}
          <div className="absolute inset-0 rounded-2xl bg-glow-gradient
                          opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

          {/* Icon */}
          <div className={`relative w-10 h-10 rounded-xl bg-gradient-to-br ${stat.bgColor}
                          flex items-center justify-center mb-4`}>
            <stat.icon className={`w-5 h-5 ${stat.color}`} />
          </div>

          {/* Value */}
          <div className="relative text-3xl font-semibold text-text-primary tracking-tight mb-1">
            {typeof stat.value === 'number' ? formatNumber(stat.value) : stat.value}
          </div>

          {/* Label */}
          <div className="relative text-sm text-text-tertiary">
            {stat.label}
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}

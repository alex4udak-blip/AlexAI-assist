import { motion } from 'framer-motion';
import { Lightbulb, TrendingUp, TrendingDown, AlertCircle, Sparkles, ArrowRight } from 'lucide-react';

interface Insight {
  id: string;
  type: 'positive' | 'negative' | 'neutral' | 'suggestion';
  message: string;
  metric?: string;
}

interface AIInsightsProps {
  insights: Insight[];
}

const insightConfig = {
  positive: {
    icon: TrendingUp,
    color: 'text-status-success',
    bg: 'bg-status-success/10',
    border: 'border-status-success/20',
  },
  negative: {
    icon: TrendingDown,
    color: 'text-status-warning',
    bg: 'bg-status-warning/10',
    border: 'border-status-warning/20',
  },
  neutral: {
    icon: AlertCircle,
    color: 'text-hud-cyan',
    bg: 'bg-hud-cyan/10',
    border: 'border-hud-cyan/20',
  },
  suggestion: {
    icon: Sparkles,
    color: 'text-hud-blue',
    bg: 'bg-hud-blue/10',
    border: 'border-hud-blue/20',
  },
};

export function AIInsights({ insights }: AIInsightsProps) {
  if (insights.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="p-4 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                   shadow-inner-glow overflow-hidden"
      >
        <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono mb-3">
          AI Insights
        </h3>
        <div className="flex flex-col items-center justify-center py-4">
          <Lightbulb className="w-7 h-7 text-text-muted mb-2" />
          <p className="text-sm text-text-muted text-center">
            Недостаточно данных
          </p>
          <p className="text-xs text-text-muted mt-1 text-center">
            AI найдет паттерны
          </p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-4 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow overflow-hidden"
    >
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className="w-4 h-4 text-hud-cyan flex-shrink-0" />
        <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono">
          AI Insights
        </h3>
      </div>

      <div className="space-y-2">
        {insights.map((insight, index) => {
          const config = insightConfig[insight.type];
          const Icon = config.icon;

          return (
            <motion.div
              key={insight.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`p-2.5 rounded-lg border ${config.bg} ${config.border}
                         hover:shadow-hud-sm transition-shadow cursor-pointer group overflow-hidden`}
            >
              <div className="flex items-start gap-2">
                <div className={`w-7 h-7 rounded-lg ${config.bg} flex items-center justify-center
                                flex-shrink-0`}>
                  <Icon className={`w-3.5 h-3.5 ${config.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-text-primary leading-relaxed line-clamp-2">
                    {insight.message}
                  </p>
                  {insight.metric && (
                    <p className={`text-[10px] font-mono mt-0.5 ${config.color} truncate`}>
                      {insight.metric}
                    </p>
                  )}
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-text-muted opacity-0 group-hover:opacity-100
                                       transition-opacity flex-shrink-0" />
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

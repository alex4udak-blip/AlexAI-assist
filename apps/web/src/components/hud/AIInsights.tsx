import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Info, Sparkles, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

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
    color: 'text-emerald-400',
  },
  negative: {
    icon: TrendingDown,
    color: 'text-amber-400',
  },
  neutral: {
    icon: Info,
    color: 'text-zinc-400',
  },
  suggestion: {
    icon: Sparkles,
    color: 'text-violet-400',
  },
};

export function AIInsights({ insights }: AIInsightsProps) {
  const navigate = useNavigate();

  const handleInsightClick = (insight: Insight) => {
    switch (insight.type) {
      case 'suggestion':
        navigate('/automation');
        break;
      case 'positive':
      case 'negative':
        navigate('/analytics');
        break;
      case 'neutral':
        navigate('/dashboard');
        break;
    }
  };

  if (insights.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800"
      >
        <h3 className="text-xs text-zinc-500 font-medium tracking-wide mb-4">
          AI Insights
        </h3>
        <div className="flex flex-col items-center justify-center py-6">
          <Sparkles className="w-6 h-6 text-zinc-600 mb-3" />
          <p className="text-sm text-zinc-400 text-center">
            Not enough data yet
          </p>
          <p className="text-xs text-zinc-600 mt-1 text-center">
            Insights will appear as patterns emerge
          </p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800"
    >
      <h3 className="text-xs text-zinc-500 font-medium tracking-wide mb-4">
        AI Insights
      </h3>

      <div className="space-y-2">
        {insights.map((insight, index) => {
          const config = insightConfig[insight.type];
          const Icon = config.icon;

          return (
            <motion.div
              key={insight.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => handleInsightClick(insight)}
              className="group flex items-start gap-3 p-3 rounded-lg bg-zinc-800/30
                         hover:bg-zinc-800/50 transition-colors cursor-pointer"
            >
              <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${config.color}`} />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-zinc-300 leading-relaxed">
                  {insight.message}
                </p>
                {insight.metric && (
                  <p className={`text-xs mt-1 ${config.color} tabular-nums`}>
                    {insight.metric}
                  </p>
                )}
              </div>
              <ChevronRight className="w-4 h-4 text-zinc-600 opacity-0 group-hover:opacity-100
                                       transition-opacity flex-shrink-0 mt-0.5" />
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

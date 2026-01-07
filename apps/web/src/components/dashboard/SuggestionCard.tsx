import { motion } from 'framer-motion';
import { Sparkles, Check, X, Clock, TrendingUp } from 'lucide-react';
import type { Suggestion } from '../../lib/api';

interface SuggestionCardProps {
  suggestion: Suggestion;
  onAccept?: (id: string) => void;
  onDismiss?: (id: string) => void;
}

const impactConfig = {
  high: {
    label: 'Высокий эффект',
    color: 'text-status-success',
    bgColor: 'bg-status-success/10',
  },
  medium: {
    label: 'Средний эффект',
    color: 'text-status-warning',
    bgColor: 'bg-status-warning/10',
  },
  low: {
    label: 'Низкий эффект',
    color: 'text-text-tertiary',
    bgColor: 'bg-white/[0.05]',
  },
};

export function SuggestionCard({ suggestion, onAccept, onDismiss }: SuggestionCardProps) {
  const impact = impactConfig[suggestion.impact as keyof typeof impactConfig] || impactConfig.low;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="group p-4 rounded-xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent
                 hover:border-border-default transition-all duration-200"
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-500/5
                        flex items-center justify-center shrink-0">
          <Sparkles className="w-5 h-5 text-amber-400" />
        </div>

        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <h4 className="font-medium text-text-primary">{suggestion.title}</h4>
            <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${impact.color} ${impact.bgColor}`}>
              {impact.label}
            </span>
          </div>

          {/* Description */}
          <p className="text-sm text-text-tertiary mb-3 line-clamp-2">
            {suggestion.description}
          </p>

          {/* Stats */}
          <div className="flex items-center gap-4 text-xs text-text-muted mb-4">
            <span className="flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5" />
              {(suggestion.confidence * 100).toFixed(0)}% уверенность
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {suggestion.time_saved_minutes}м/день
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => onAccept?.(suggestion.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                         bg-status-success/10 text-status-success text-sm font-medium
                         hover:bg-status-success/20 transition-colors"
            >
              <Check className="w-4 h-4" />
              Принять
            </button>
            <button
              onClick={() => onDismiss?.(suggestion.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                         text-text-tertiary text-sm font-medium
                         hover:bg-white/[0.05] hover:text-text-secondary transition-colors"
            >
              <X className="w-4 h-4" />
              Отклонить
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

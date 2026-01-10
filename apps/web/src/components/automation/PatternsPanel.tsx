import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import {
  Sparkles,
  TrendingUp,
  Clock,
  Repeat,
  ChevronRight,
  X,
  Loader2,
  AlertCircle,
  Zap,
  Bot,
} from 'lucide-react';
import { useSuggestions, useDetectPatterns } from '../../hooks/usePatterns';
import { useMutation } from '../../hooks/useApi';
import { api, type Suggestion } from '../../lib/api';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

interface PatternsPanelProps {
  onAgentCreated?: (agentId: string) => void;
}

export function PatternsPanel({ onAgentCreated }: PatternsPanelProps) {
  const { data: suggestions, refetch: refetchSuggestions, loading: suggestionsLoading } = useSuggestions({ status: 'pending' });
  const { data: detectedPatterns, loading: patternsLoading } = useDetectPatterns();
  const { mutate: acceptSuggestion, loading: accepting } = useMutation(api.acceptSuggestion);
  const { mutate: dismissSuggestion, loading: dismissing } = useMutation(api.dismissSuggestion);

  const [processingId, setProcessingId] = useState<string | null>(null);

  const handleAccept = async (suggestion: Suggestion) => {
    setProcessingId(suggestion.id);
    try {
      const result = await acceptSuggestion(suggestion.id);
      if (result?.agent_id && onAgentCreated) {
        onAgentCreated(result.agent_id);
      }
      refetchSuggestions();
    } catch (error) {
      console.error('Failed to accept suggestion:', error);
    } finally {
      setProcessingId(null);
    }
  };

  const handleDismiss = async (suggestion: Suggestion) => {
    setProcessingId(suggestion.id);
    try {
      await dismissSuggestion(suggestion.id);
      refetchSuggestions();
    } catch (error) {
      console.error('Failed to dismiss suggestion:', error);
    } finally {
      setProcessingId(null);
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact.toLowerCase()) {
      case 'high':
        return 'text-emerald-400 bg-emerald-400/10';
      case 'medium':
        return 'text-amber-400 bg-amber-400/10';
      case 'low':
        return 'text-zinc-400 bg-zinc-400/10';
      default:
        return 'text-zinc-400 bg-zinc-400/10';
    }
  };

  const getImpactLabel = (impact: string) => {
    switch (impact.toLowerCase()) {
      case 'high':
        return 'Высокий';
      case 'medium':
        return 'Средний';
      case 'low':
        return 'Низкий';
      default:
        return impact;
    }
  };

  const isLoading = suggestionsLoading || patternsLoading;
  const hasSuggestions = suggestions && suggestions.length > 0;
  const hasPatterns = detectedPatterns && (
    detectedPatterns.app_sequences.length > 0 ||
    detectedPatterns.time_patterns.length > 0
  );

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Suggestions Section */}
      <motion.div variants={item}>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-violet-400" />
                <CardTitle>Рекомендации для автоматизации</CardTitle>
              </div>
              {hasSuggestions && (
                <span className="text-xs text-text-tertiary bg-bg-tertiary px-2 py-1 rounded-full">
                  {suggestions.length} {suggestions.length === 1 ? 'рекомендация' : 'рекомендаций'}
                </span>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-accent-primary animate-spin" />
              </div>
            ) : hasSuggestions ? (
              <div className="space-y-3">
                <AnimatePresence mode="popLayout">
                  {suggestions.map((suggestion) => (
                    <motion.div
                      key={suggestion.id}
                      layout
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="p-4 rounded-lg bg-bg-tertiary border border-border-default
                                 hover:border-border-hover transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-sm font-medium text-text-primary truncate">
                              {suggestion.title}
                            </h4>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${getImpactColor(suggestion.impact)}`}>
                              {getImpactLabel(suggestion.impact)}
                            </span>
                          </div>
                          {suggestion.description && (
                            <p className="text-sm text-text-secondary mb-2 line-clamp-2">
                              {suggestion.description}
                            </p>
                          )}
                          <div className="flex items-center gap-4 text-xs text-text-tertiary">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {suggestion.time_saved_minutes}м экономии
                            </span>
                            <span className="flex items-center gap-1">
                              <Zap className="w-3 h-3" />
                              {Math.round(suggestion.confidence * 100)}% уверенность
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDismiss(suggestion)}
                            disabled={processingId === suggestion.id}
                            className="h-8 w-8 p-0"
                            title="Отклонить"
                          >
                            {processingId === suggestion.id && dismissing ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <X className="w-4 h-4 text-text-tertiary hover:text-status-error" />
                            )}
                          </Button>
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => handleAccept(suggestion)}
                            disabled={processingId === suggestion.id}
                            className="h-8"
                          >
                            {processingId === suggestion.id && accepting ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <>
                                <Bot className="w-4 h-4" />
                                Создать агента
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <AlertCircle className="w-8 h-8 text-text-tertiary mb-3" />
                <p className="text-sm text-text-secondary">
                  Пока нет рекомендаций для автоматизации
                </p>
                <p className="text-xs text-text-tertiary mt-1">
                  Рекомендации появятся по мере анализа ваших паттернов активности
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Detected Patterns Section */}
      <motion.div variants={item}>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              <CardTitle>Обнаруженные паттерны</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-accent-primary animate-spin" />
              </div>
            ) : hasPatterns ? (
              <div className="space-y-4">
                {/* App Sequences */}
                {detectedPatterns.app_sequences.length > 0 && (
                  <div>
                    <h5 className="text-xs text-text-tertiary uppercase tracking-wider mb-3 flex items-center gap-2">
                      <Repeat className="w-3 h-3" />
                      Последовательности приложений
                    </h5>
                    <div className="space-y-2">
                      {detectedPatterns.app_sequences.map((seq, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 rounded-lg bg-bg-tertiary"
                        >
                          <div className="flex items-center gap-2 flex-wrap flex-1 min-w-0">
                            {seq.sequence.map((app, appIndex) => (
                              <span key={appIndex} className="flex items-center gap-1">
                                <span className="text-sm text-text-primary bg-bg-secondary px-2 py-0.5 rounded">
                                  {app}
                                </span>
                                {appIndex < seq.sequence.length - 1 && (
                                  <ChevronRight className="w-3 h-3 text-text-tertiary" />
                                )}
                              </span>
                            ))}
                          </div>
                          <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                            <span className="text-xs text-text-tertiary">
                              {seq.occurrences}x
                            </span>
                            {seq.automatable && (
                              <span className="text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">
                                Автоматизируемо
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Time Patterns */}
                {detectedPatterns.time_patterns.length > 0 && (
                  <div>
                    <h5 className="text-xs text-text-tertiary uppercase tracking-wider mb-3 flex items-center gap-2">
                      <Clock className="w-3 h-3" />
                      Временные паттерны
                    </h5>
                    <div className="space-y-2">
                      {detectedPatterns.time_patterns.map((pattern, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 rounded-lg bg-bg-tertiary"
                        >
                          <div className="flex items-center gap-3">
                            <span className="text-lg font-mono text-accent-primary">
                              {pattern.hour.toString().padStart(2, '0')}:00
                            </span>
                            <span className="text-sm text-text-primary">
                              {pattern.app}
                            </span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-text-tertiary">
                              {pattern.occurrences} раз
                            </span>
                            {pattern.automatable && (
                              <span className="text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">
                                Автоматизируемо
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Context Switches */}
                {detectedPatterns.context_switches && (
                  <div className="p-4 rounded-lg bg-bg-tertiary">
                    <h5 className="text-xs text-text-tertiary uppercase tracking-wider mb-2">
                      Переключения контекста
                    </h5>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xl font-bold text-text-primary">
                          {detectedPatterns.context_switches.total_switches}
                        </p>
                        <p className="text-xs text-text-tertiary">
                          переключений ({detectedPatterns.context_switches.switch_rate.toFixed(1)}/час)
                        </p>
                      </div>
                      <span className={`text-sm px-3 py-1 rounded-full ${
                        detectedPatterns.context_switches.assessment === 'low'
                          ? 'text-emerald-400 bg-emerald-400/10'
                          : detectedPatterns.context_switches.assessment === 'moderate'
                          ? 'text-amber-400 bg-amber-400/10'
                          : 'text-red-400 bg-red-400/10'
                      }`}>
                        {detectedPatterns.context_switches.assessment === 'low'
                          ? 'Низкий уровень'
                          : detectedPatterns.context_switches.assessment === 'moderate'
                          ? 'Умеренный уровень'
                          : 'Высокий уровень'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <TrendingUp className="w-8 h-8 text-text-tertiary mb-3" />
                <p className="text-sm text-text-secondary">
                  Паттерны пока не обнаружены
                </p>
                <p className="text-xs text-text-tertiary mt-1">
                  Система анализирует вашу активность для выявления закономерностей
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}

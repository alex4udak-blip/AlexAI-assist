import { Target } from 'lucide-react';

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
      <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent">
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
      </div>
    );
  }

  const score = data?.score ?? 0;

  const getScoreColor = () => {
    if (score >= 70) return { stroke: '#10B981', glow: 'rgba(16, 185, 129, 0.3)' };
    if (score >= 40) return { stroke: '#F59E0B', glow: 'rgba(245, 158, 11, 0.3)' };
    return { stroke: '#EF4444', glow: 'rgba(239, 68, 68, 0.3)' };
  };

  const colors = getScoreColor();
  const circumference = 2 * Math.PI * 44;
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <div className="p-6 rounded-2xl border border-border-subtle bg-gradient-to-br from-white/[0.02] to-transparent">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-500/5
                          flex items-center justify-center">
            <Target className="w-5 h-5 text-emerald-400" />
          </div>
          <h3 className="text-lg font-semibold text-text-primary tracking-tight">
            Продуктивность
          </h3>
        </div>
{/* Trend indicator removed - no real comparison data from backend */}
      </div>

      <div className="flex items-center gap-8">
        {/* Score Ring */}
        <div className="relative w-32 h-32 shrink-0">
          <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 100 100">
            {/* Background circle */}
            <circle
              cx="50"
              cy="50"
              r="44"
              stroke="rgba(255, 255, 255, 0.05)"
              strokeWidth="6"
              fill="none"
            />
            {/* Progress circle */}
            <circle
              cx="50"
              cy="50"
              r="44"
              stroke={colors.stroke}
              strokeWidth="6"
              fill="none"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              strokeLinecap="round"
              style={{
                filter: `drop-shadow(0 0 8px ${colors.glow})`,
                transition: 'stroke-dashoffset 0.5s ease-out',
              }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold text-text-primary">{score}</span>
            <span className="text-xs text-text-muted">из 100</span>
          </div>
        </div>

        {/* Stats */}
        <div className="flex-1 space-y-4">
          <div className="p-3 rounded-xl bg-white/[0.02]">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-text-tertiary">Продуктивных</span>
              <span className="text-sm font-medium text-text-primary">
                {data?.productive_events ?? 0}
              </span>
            </div>
            <div className="h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
              <div
                className="h-full bg-status-success rounded-full transition-all duration-500"
                style={{
                  width: `${data?.total_events ? (data.productive_events / data.total_events) * 100 : 0}%`,
                }}
              />
            </div>
          </div>

          <div className="p-3 rounded-xl bg-white/[0.02]">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-text-tertiary">Всего событий</span>
              <span className="text-sm font-medium text-text-primary">
                {data?.total_events ?? 0}
              </span>
            </div>
            <div className="h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
              <div className="h-full bg-accent-primary rounded-full w-full" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

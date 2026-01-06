import { cn } from '../../lib/utils';

interface ProgressProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'success' | 'warning' | 'error';
  showLabel?: boolean;
  className?: string;
}

export function Progress({
  value,
  max = 100,
  size = 'md',
  variant = 'default',
  showLabel = false,
  className,
}: ProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const sizes = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  const variants = {
    default: 'bg-accent-primary',
    success: 'bg-status-success',
    warning: 'bg-status-warning',
    error: 'bg-status-error',
  };

  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between text-sm text-text-secondary mb-1">
          <span>{value}</span>
          <span>{percentage.toFixed(0)}%</span>
        </div>
      )}
      <div
        className={cn('w-full bg-bg-tertiary rounded-full overflow-hidden', sizes[size])}
      >
        <div
          className={cn('h-full rounded-full transition-all duration-300', variants[variant])}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

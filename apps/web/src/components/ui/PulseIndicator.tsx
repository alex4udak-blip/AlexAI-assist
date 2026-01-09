import { type HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../lib/utils';

interface PulseIndicatorProps extends HTMLAttributes<HTMLDivElement> {
  status: 'active' | 'processing' | 'warning' | 'error' | 'offline';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  label?: string;
}

export const PulseIndicator = forwardRef<HTMLDivElement, PulseIndicatorProps>(
  (
    {
      className,
      status,
      size = 'md',
      showLabel = false,
      label,
      ...props
    },
    ref
  ) => {
    const statusConfig = {
      active: {
        color: 'bg-status-success',
        shadowColor: 'shadow-glow-green',
        textColor: 'text-status-success',
        label: 'Active',
      },
      processing: {
        color: 'bg-hud-blue',
        shadowColor: 'shadow-glow-blue',
        textColor: 'text-hud-blue',
        label: 'Processing',
      },
      warning: {
        color: 'bg-status-warning',
        shadowColor: 'shadow-glow-orange',
        textColor: 'text-status-warning',
        label: 'Warning',
      },
      error: {
        color: 'bg-status-error',
        shadowColor: 'shadow-[0_0_20px_rgba(239,68,68,0.5)]',
        textColor: 'text-status-error',
        label: 'Error',
      },
      offline: {
        color: 'bg-status-offline',
        shadowColor: '',
        textColor: 'text-status-offline',
        label: 'Offline',
      },
    };

    const sizes = {
      sm: 'w-2 h-2',
      md: 'w-3 h-3',
      lg: 'w-4 h-4',
    };

    const config = statusConfig[status];
    const displayLabel = label || config.label;

    return (
      <div
        ref={ref}
        className={cn('inline-flex items-center gap-2', className)}
        {...props}
      >
        <div className="relative">
          {/* Pulse ring */}
          {status !== 'offline' && (
            <span
              className={cn(
                'absolute inset-0 rounded-full animate-ping opacity-75',
                config.color
              )}
            />
          )}
          {/* Core dot */}
          <span
            className={cn(
              'relative inline-block rounded-full',
              sizes[size],
              config.color,
              status !== 'offline' && config.shadowColor
            )}
          />
        </div>
        {showLabel && (
          <span
            className={cn(
              'text-sm font-medium',
              config.textColor
            )}
          >
            {displayLabel}
          </span>
        )}
      </div>
    );
  }
);

PulseIndicator.displayName = 'PulseIndicator';

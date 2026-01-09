import { type HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../lib/utils';

interface NeonTextProps extends HTMLAttributes<HTMLSpanElement> {
  intensity?: 'subtle' | 'medium' | 'bright';
  color?: 'cyan' | 'blue' | 'green' | 'orange' | 'violet';
  animated?: boolean;
}

export const NeonText = forwardRef<HTMLSpanElement, NeonTextProps>(
  (
    {
      className,
      intensity = 'medium',
      color = 'cyan',
      animated = false,
      children,
      ...props
    },
    ref
  ) => {
    const colors = {
      cyan: 'text-hud-cyan',
      blue: 'text-hud-blue',
      green: 'text-status-success',
      orange: 'text-ring-outer',
      violet: 'text-ring-middle',
    };

    const intensities = {
      subtle: 'drop-shadow-[0_0_8px_currentColor]',
      medium: 'drop-shadow-[0_0_12px_currentColor] drop-shadow-[0_0_4px_currentColor]',
      bright:
        'drop-shadow-[0_0_20px_currentColor] drop-shadow-[0_0_8px_currentColor] drop-shadow-[0_0_4px_currentColor]',
    };

    return (
      <span
        ref={ref}
        className={cn(
          'font-medium tracking-wide',
          colors[color],
          intensities[intensity],
          animated && 'animate-pulse-glow',
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

NeonText.displayName = 'NeonText';

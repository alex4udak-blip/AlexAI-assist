import { type HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../lib/utils';

interface CircuitPatternProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'dense' | 'minimal';
  animated?: boolean;
  opacity?: number;
}

export const CircuitPattern = forwardRef<HTMLDivElement, CircuitPatternProps>(
  (
    {
      className,
      variant = 'default',
      animated = true,
      opacity = 0.15,
      ...props
    },
    ref
  ) => {
    const variantConfig = {
      default: { gridSize: 40, strokeWidth: 1 },
      dense: { gridSize: 20, strokeWidth: 0.5 },
      minimal: { gridSize: 80, strokeWidth: 1.5 },
    };

    const config = variantConfig[variant];

    return (
      <div
        ref={ref}
        className={cn('absolute inset-0 overflow-hidden pointer-events-none', className)}
        style={{ opacity }}
        {...props}
      >
        <svg
          className="w-full h-full"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <pattern
              id="circuit-pattern"
              x="0"
              y="0"
              width={config.gridSize}
              height={config.gridSize}
              patternUnits="userSpaceOnUse"
            >
              {/* Horizontal lines */}
              <line
                x1="0"
                y1={config.gridSize / 2}
                x2={config.gridSize}
                y2={config.gridSize / 2}
                stroke="rgba(6, 182, 212, 0.3)"
                strokeWidth={config.strokeWidth}
              />
              {/* Vertical lines */}
              <line
                x1={config.gridSize / 2}
                y1="0"
                x2={config.gridSize / 2}
                y2={config.gridSize}
                stroke="rgba(6, 182, 212, 0.3)"
                strokeWidth={config.strokeWidth}
              />
              {/* Corner nodes */}
              <circle
                cx={config.gridSize / 2}
                cy={config.gridSize / 2}
                r={config.strokeWidth * 2}
                fill="rgba(6, 182, 212, 0.5)"
              >
                {animated && (
                  <animate
                    attributeName="r"
                    values={`${config.strokeWidth * 2};${config.strokeWidth * 3};${config.strokeWidth * 2}`}
                    dur="3s"
                    repeatCount="indefinite"
                  />
                )}
              </circle>
              {/* Diagonal accent */}
              <line
                x1={config.gridSize / 4}
                y1={config.gridSize / 2}
                x2={config.gridSize / 2}
                y2={config.gridSize / 4}
                stroke="rgba(6, 182, 212, 0.2)"
                strokeWidth={config.strokeWidth}
              />
            </pattern>

            {/* Pulse gradient */}
            {animated && (
              <linearGradient id="pulse-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgba(6, 182, 212, 0)">
                  <animate
                    attributeName="stop-color"
                    values="rgba(6, 182, 212, 0);rgba(6, 182, 212, 0.3);rgba(6, 182, 212, 0)"
                    dur="3s"
                    repeatCount="indefinite"
                  />
                </stop>
                <stop offset="50%" stopColor="rgba(6, 182, 212, 0.3)">
                  <animate
                    attributeName="stop-color"
                    values="rgba(6, 182, 212, 0.3);rgba(6, 182, 212, 0);rgba(6, 182, 212, 0.3)"
                    dur="3s"
                    repeatCount="indefinite"
                  />
                </stop>
                <stop offset="100%" stopColor="rgba(6, 182, 212, 0)">
                  <animate
                    attributeName="stop-color"
                    values="rgba(6, 182, 212, 0);rgba(6, 182, 212, 0.3);rgba(6, 182, 212, 0)"
                    dur="3s"
                    repeatCount="indefinite"
                  />
                </stop>
              </linearGradient>
            )}
          </defs>

          {/* Apply pattern */}
          <rect width="100%" height="100%" fill="url(#circuit-pattern)" />

          {/* Animated overlay */}
          {animated && (
            <rect
              width="100%"
              height="100%"
              fill="url(#pulse-gradient)"
              opacity="0.5"
            />
          )}
        </svg>
      </div>
    );
  }
);

CircuitPattern.displayName = 'CircuitPattern';

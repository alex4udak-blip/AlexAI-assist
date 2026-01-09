import { type HTMLAttributes, forwardRef, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface HolographicCardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'interactive';
  showCorners?: boolean;
  showScanline?: boolean;
  animated?: boolean;
  children?: ReactNode;
}

export const HolographicCard = forwardRef<HTMLDivElement, HolographicCardProps>(
  (
    {
      className,
      variant = 'default',
      showCorners = true,
      showScanline = false,
      animated = true,
      children,
      ...props
    },
    ref
  ) => {
    const variants = {
      default: 'border-border-default',
      interactive: 'border-border-subtle hover:border-border-glow cursor-pointer hover:shadow-hud',
    };

    const classNames = cn(
      'relative rounded-xl p-5 overflow-hidden',
      'bg-gradient-to-br from-surface-primary to-bg-secondary',
      'border transition-all duration-300',
      variants[variant],
      className
    );

    const content = (
      <>
        {/* Animated gradient border */}
        <div
          className="absolute inset-0 rounded-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100 pointer-events-none"
          style={{
            background:
              'linear-gradient(90deg, transparent, rgba(6, 182, 212, 0.3), transparent)',
            animation: 'border-flow 3s linear infinite',
          }}
        />

        {/* Corner accents */}
        {showCorners && (
          <>
            <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-hud-cyan" />
            <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-hud-cyan" />
            <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-hud-cyan" />
            <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-hud-cyan" />
          </>
        )}

        {/* Scanline effect */}
        {showScanline && (
          <div
            className="absolute inset-0 pointer-events-none opacity-30"
            style={{
              backgroundImage:
                'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(6, 182, 212, 0.05) 2px, rgba(6, 182, 212, 0.05) 4px)',
            }}
          />
        )}

        <div className="relative z-10">{children}</div>
      </>
    );

    if (animated) {
      return (
        <motion.div
          ref={ref}
          className={classNames}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          {...(props as Record<string, unknown>)}
        >
          {content}
        </motion.div>
      );
    }

    return (
      <div ref={ref} className={classNames} {...props}>
        {content}
      </div>
    );
  }
);

HolographicCard.displayName = 'HolographicCard';

import { type HTMLAttributes, forwardRef, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface GlassPanelProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'glow';
  animated?: boolean;
  children?: ReactNode;
}

export const GlassPanel = forwardRef<HTMLDivElement, GlassPanelProps>(
  ({ className, variant = 'default', animated = true, children, ...props }, ref) => {
    const variants = {
      default: 'bg-glass border border-border-subtle',
      elevated: 'bg-glass border border-border-default shadow-hud-sm',
      glow: 'bg-glass border border-border-glow shadow-hud',
    };

    const classNames = cn(
      'rounded-xl p-5 backdrop-blur-xl',
      'transition-all duration-300 ease-out-expo',
      'hover:border-border-default hover:shadow-hud-sm',
      variants[variant],
      className
    );

    if (animated) {
      return (
        <motion.div
          ref={ref}
          className={classNames}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          {...(props as Record<string, unknown>)}
        >
          {children}
        </motion.div>
      );
    }

    return (
      <div ref={ref} className={classNames} {...props}>
        {children}
      </div>
    );
  }
);

GlassPanel.displayName = 'GlassPanel';

import { motion } from 'framer-motion';
import { ReactNode } from 'react';
import { CircuitPattern as CircuitPatternComponent } from '../ui/CircuitPattern';

// Scan line effect for HUD headers
export function ScanLine() {
  return (
    <motion.div
      className="absolute inset-0 pointer-events-none overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <motion.div
        className="absolute w-full h-[2px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent"
        animate={{
          y: ['-100%', '500%'],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: 'linear',
          repeatDelay: 2,
        }}
      />
    </motion.div>
  );
}

// Holographic card wrapper with glassmorphism
interface HoloCardProps {
  children: ReactNode;
  className?: string;
  glowColor?: 'cyan' | 'purple' | 'green' | 'red' | 'amber' | 'blue' | 'emerald' | 'violet';
}

const glowStyles = {
  cyan: 'shadow-[0_0_20px_rgba(6,182,212,0.15)] border-cyan-500/20',
  purple: 'shadow-[0_0_20px_rgba(168,85,247,0.15)] border-purple-500/20',
  green: 'shadow-[0_0_20px_rgba(16,185,129,0.15)] border-emerald-500/20',
  red: 'shadow-[0_0_20px_rgba(239,68,68,0.15)] border-red-500/20',
  amber: 'shadow-[0_0_20px_rgba(245,158,11,0.15)] border-amber-500/20',
  blue: 'shadow-[0_0_20px_rgba(59,130,246,0.15)] border-blue-500/20',
  emerald: 'shadow-[0_0_20px_rgba(16,185,129,0.15)] border-emerald-500/20',
  violet: 'shadow-[0_0_20px_rgba(139,92,246,0.15)] border-violet-500/20',
};

export function HoloCard({ children, className = '', glowColor = 'cyan' }: HoloCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative p-6 rounded-2xl border backdrop-blur-xl
                  bg-gradient-to-br from-white/[0.05] to-white/[0.01]
                  ${glowStyles[glowColor]}
                  ${className}`}
    >
      <CircuitPatternComponent variant="minimal" opacity={0.05} />
      <div className="relative z-10">{children}</div>

      {/* Corner accents */}
      <div className="absolute top-0 left-0 w-12 h-12 border-t-2 border-l-2 border-cyan-500/30 rounded-tl-2xl" />
      <div className="absolute bottom-0 right-0 w-12 h-12 border-b-2 border-r-2 border-cyan-500/30 rounded-br-2xl" />
    </motion.div>
  );
}

// HUD-style section header
interface HudHeaderProps {
  icon: ReactNode;
  title: string;
  iconColor?: string;
  glowColor?: string;
}

export function HudHeader({ icon, title, iconColor = 'cyan', glowColor = 'cyan' }: HudHeaderProps) {
  return (
    <div className="relative flex items-center gap-3 mb-6">
      <ScanLine />
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15 }}
        className={`relative w-10 h-10 rounded-xl bg-gradient-to-br from-${iconColor}-500/30 to-${iconColor}-500/5
                    flex items-center justify-center
                    shadow-[0_0_15px_rgba(6,182,212,0.3)]`}
        style={{
          boxShadow: `0 0 20px ${glowColor === 'cyan' ? 'rgba(6,182,212,0.3)' :
                                 glowColor === 'purple' ? 'rgba(168,85,247,0.3)' :
                                 glowColor === 'green' ? 'rgba(16,185,129,0.3)' :
                                 glowColor === 'amber' ? 'rgba(245,158,11,0.3)' :
                                 glowColor === 'blue' ? 'rgba(59,130,246,0.3)' :
                                 glowColor === 'emerald' ? 'rgba(16,185,129,0.3)' :
                                 'rgba(139,92,246,0.3)'}`,
        }}
      >
        {icon}
        {/* Pulsing ring */}
        <motion.div
          className={`absolute inset-0 rounded-xl border-2 border-${iconColor}-400`}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.5, 0, 0.5],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </motion.div>
      <h3 className="text-lg font-semibold text-text-primary tracking-tight font-mono">
        {title}
      </h3>
      {/* Horizontal line */}
      <div className="flex-1 h-[1px] bg-gradient-to-r from-cyan-500/50 via-cyan-500/10 to-transparent ml-3" />
    </div>
  );
}

// Pulsing data indicator
export function PulsingIndicator({ color = 'cyan' }: { color?: string }) {
  return (
    <motion.div
      className={`w-2 h-2 rounded-full bg-${color}-400`}
      animate={{
        scale: [1, 1.5, 1],
        opacity: [1, 0.5, 1],
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
      style={{
        boxShadow: `0 0 10px ${color === 'cyan' ? '#06b6d4' :
                                color === 'green' ? '#10b981' :
                                color === 'purple' ? '#a855f7' : '#06b6d4'}`,
      }}
    />
  );
}

// Animated grid overlay for charts
export function AnimatedGrid() {
  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-10" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-cyan-400" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
      <motion.rect
        width="100%"
        height="100%"
        fill="url(#grid)"
        animate={{
          opacity: [0.1, 0.3, 0.1],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </svg>
  );
}

// Holographic shimmer effect
export function HolographicShimmer() {
  return (
    <motion.div
      className="absolute inset-0 pointer-events-none overflow-hidden rounded-2xl"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/10 to-transparent"
        animate={{
          x: ['-200%', '200%'],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: 'linear',
          repeatDelay: 3,
        }}
      />
    </motion.div>
  );
}

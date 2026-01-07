import { motion } from 'framer-motion';
import { Monitor, Globe, FileText, Code, MessageSquare } from 'lucide-react';

interface MobileHeaderProps {
  productivity: number;
  focus: number;
  automation: number;
  focusTime?: number;
  currentApp?: string;
  category?: string;
}

const appIcons: Record<string, typeof Monitor> = {
  browser: Globe,
  code: Code,
  document: FileText,
  communication: MessageSquare,
  default: Monitor,
};

export function MobileHeader({
  productivity,
  focus,
  automation,
  focusTime = 0,
  currentApp,
  category,
}: MobileHeaderProps) {
  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}ч ${mins}м`;
    }
    return `${mins}м`;
  };

  const AppIcon = appIcons[category || 'default'] || Monitor;

  const rings = [
    { value: productivity, color: '#f97316', label: 'P' },
    { value: focus, color: '#8b5cf6', label: 'F' },
    { value: automation, color: '#10b981', label: 'A' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky top-0 z-40 px-4 py-3 bg-bg-primary/95 backdrop-blur-lg border-b border-border-subtle
                 safe-area-top overflow-hidden"
    >
      <div className="flex items-center justify-between gap-3">
        {/* Compact Activity Rings */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {rings.map((ring, index) => (
            <div key={index} className="relative w-9 h-9">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                {/* Background circle */}
                <circle
                  cx="18"
                  cy="18"
                  r="14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  className="text-white/5"
                />
                {/* Progress circle */}
                <motion.circle
                  cx="18"
                  cy="18"
                  r="14"
                  fill="none"
                  stroke={ring.color}
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeDasharray={`${(ring.value / 100) * 88} 88`}
                  initial={{ strokeDasharray: '0 88' }}
                  animate={{ strokeDasharray: `${(ring.value / 100) * 88} 88` }}
                  transition={{ duration: 1, delay: index * 0.1 }}
                />
              </svg>
              <span
                className="absolute inset-0 flex items-center justify-center text-[9px] font-mono font-bold"
                style={{ color: ring.color }}
              >
                {ring.label}
              </span>
            </div>
          ))}
        </div>

        {/* Focus Status */}
        <div className="flex items-center gap-2 min-w-0">
          <div className="text-right min-w-0">
            <p className="text-[10px] text-text-muted">В фокусе</p>
            <p className="text-sm font-mono font-bold text-hud-cyan">
              {formatTime(focusTime)}
            </p>
          </div>
          <div className="w-9 h-9 rounded-lg bg-bg-tertiary flex items-center justify-center flex-shrink-0">
            <AppIcon className="w-4 h-4 text-hud-cyan" />
          </div>
        </div>
      </div>

      {/* Current App */}
      {currentApp && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-1.5 text-center overflow-hidden"
        >
          <span className="text-[10px] text-text-muted truncate block">
            {currentApp}
          </span>
        </motion.div>
      )}
    </motion.div>
  );
}

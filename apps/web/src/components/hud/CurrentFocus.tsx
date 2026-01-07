import { motion } from 'framer-motion';
import { Monitor, Clock, Zap } from 'lucide-react';
import { useEffect, useState } from 'react';

interface CurrentFocusProps {
  appName?: string;
  appIcon?: string;
  sessionMinutes?: number;
  category?: string;
}

export function CurrentFocus({
  appName,
  sessionMinutes = 0,
  category,
}: CurrentFocusProps) {
  const [displayTime, setDisplayTime] = useState(sessionMinutes);

  useEffect(() => {
    const interval = setInterval(() => {
      setDisplayTime((t) => t + 1);
    }, 60000); // Update every minute

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    setDisplayTime(sessionMinutes);
  }, [sessionMinutes]);

  const formatTime = (minutes: number) => {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0) {
      return `${h}:${m.toString().padStart(2, '0')}`;
    }
    return `${m}м`;
  };

  if (!appName) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="p-5 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                   shadow-inner-glow flex flex-col items-center justify-center min-h-[160px]"
      >
        <Monitor className="w-8 h-8 text-text-muted mb-2" />
        <p className="text-sm text-text-muted">Ожидание активности...</p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="p-4 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow relative overflow-hidden"
    >
      {/* Animated background glow */}
      <div className="absolute inset-0 bg-hud-radial opacity-50 pointer-events-none" />

      <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono mb-4 relative">
        Current Focus
      </h3>

      <div className="relative">
        {/* App Icon & Name */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-14 h-14 rounded-xl bg-hud-gradient border border-border-default
                          flex items-center justify-center shadow-hud flex-shrink-0">
            <Monitor className="w-7 h-7 text-hud-cyan" />
          </div>
          <div className="min-w-0 flex-1">
            <h4 className="text-lg font-semibold text-text-primary truncate">{appName}</h4>
            {category && (
              <span className="text-xs font-mono text-hud-cyan uppercase tracking-wider">
                {category}
              </span>
            )}
          </div>
        </div>

        {/* Timer */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-hud-muted
                          border border-border-subtle">
            <Clock className="w-4 h-4 text-hud-cyan" />
            <span className="text-2xl font-mono font-bold text-text-primary">
              {formatTime(displayTime)}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <Zap className="w-3.5 h-3.5 text-status-success" />
            <span>Активная сессия</span>
          </div>
        </div>
      </div>

      {/* Scanline effect */}
      <div className="absolute inset-0 bg-scanline pointer-events-none opacity-30" />
    </motion.div>
  );
}

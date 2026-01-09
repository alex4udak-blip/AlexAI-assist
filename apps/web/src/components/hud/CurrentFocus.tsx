import { motion } from 'framer-motion';
import { Monitor, Clock } from 'lucide-react';
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
    return `${m}m`;
  };

  if (!appName) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800
                   flex flex-col items-center justify-center min-h-[160px]"
      >
        <Monitor className="w-7 h-7 text-zinc-600 mb-3" />
        <p className="text-sm text-zinc-500">Waiting for activity...</p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800"
    >
      <h3 className="text-xs text-zinc-500 font-medium tracking-wide mb-4">
        Current Focus
      </h3>

      {/* App Icon & Name */}
      <div className="flex items-center gap-4 mb-5">
        <div className="w-12 h-12 rounded-xl bg-zinc-800 border border-zinc-700
                        flex items-center justify-center flex-shrink-0">
          <Monitor className="w-6 h-6 text-zinc-400" />
        </div>
        <div className="min-w-0 flex-1">
          <h4 className="text-lg font-semibold text-zinc-100 truncate">{appName}</h4>
          {category && (
            <span className="text-xs text-zinc-500">
              {category}
            </span>
          )}
        </div>
      </div>

      {/* Timer */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg bg-zinc-800/50
                        border border-zinc-700/50">
          <Clock className="w-4 h-4 text-zinc-500" />
          <span className="text-2xl font-semibold text-zinc-100 tabular-nums">
            {formatTime(displayTime)}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="text-sm text-zinc-400">Active session</span>
        </div>
      </div>
    </motion.div>
  );
}

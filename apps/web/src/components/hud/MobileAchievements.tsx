import { motion } from 'framer-motion';
import { Trophy, Flame, Zap, Clock, Bot, Target } from 'lucide-react';

interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: 'trophy' | 'flame' | 'zap' | 'clock' | 'bot' | 'target';
  progress: number;
  completed: boolean;
  value?: string;
}

interface MobileAchievementsProps {
  achievements: Achievement[];
  streak?: number;
}

const iconMap = {
  trophy: Trophy,
  flame: Flame,
  zap: Zap,
  clock: Clock,
  bot: Bot,
  target: Target,
};

export function MobileAchievements({ achievements, streak = 0 }: MobileAchievementsProps) {
  return (
    <div className="py-4">
      {/* Header */}
      <div className="flex items-center justify-between px-4 mb-3">
        <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono">
          Достижения
        </h3>
        {streak > 0 && (
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-status-warning/10
                          border border-status-warning/20">
            <Flame className="w-3 h-3 text-status-warning" />
            <span className="text-[10px] font-mono font-bold text-status-warning">
              {streak}
            </span>
          </div>
        )}
      </div>

      {/* Horizontal scroll container */}
      <div className="overflow-x-auto scrollbar-hide">
        <div className="flex gap-3 px-4 pb-2" style={{ minWidth: 'min-content' }}>
          {achievements.map((achievement, index) => {
            const Icon = iconMap[achievement.icon];
            const isCompleted = achievement.completed;

            return (
              <motion.div
                key={achievement.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.05 }}
                className={`flex-shrink-0 w-32 p-3 rounded-xl border transition-all
                           ${isCompleted
                             ? 'bg-hud-cyan/10 border-hud-cyan/30'
                             : 'bg-bg-secondary/60 border-border-subtle'
                           }`}
              >
                {/* Icon */}
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-2
                                ${isCompleted ? 'bg-hud-cyan/20' : 'bg-bg-tertiary'}`}>
                  <Icon className={`w-5 h-5 ${isCompleted ? 'text-hud-cyan' : 'text-text-muted'}`} />
                </div>

                {/* Title */}
                <h4 className={`text-xs font-medium mb-1 line-clamp-1
                               ${isCompleted ? 'text-text-primary' : 'text-text-secondary'}`}>
                  {achievement.title}
                </h4>

                {/* Progress or completed badge */}
                {isCompleted ? (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-hud-cyan/20 text-hud-cyan">
                    DONE
                  </span>
                ) : (
                  <div className="mt-1">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[10px] text-text-muted font-mono">
                        {achievement.progress}%
                      </span>
                      {achievement.value && (
                        <span className="text-[10px] text-hud-cyan font-mono">
                          {achievement.value}
                        </span>
                      )}
                    </div>
                    <div className="h-1 bg-bg-tertiary rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${achievement.progress}%` }}
                        transition={{ duration: 0.5, delay: index * 0.1 }}
                        className="h-full bg-hud-gradient rounded-full"
                      />
                    </div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

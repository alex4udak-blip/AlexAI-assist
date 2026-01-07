import { motion } from 'framer-motion';
import { Trophy, Flame, Zap, Clock, Bot, Target } from 'lucide-react';

interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: 'trophy' | 'flame' | 'zap' | 'clock' | 'bot' | 'target';
  progress: number; // 0-100
  completed: boolean;
  value?: string;
}

interface AchievementsProps {
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

export function Achievements({ achievements, streak = 0 }: AchievementsProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-4 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow overflow-hidden"
    >
      <div className="flex items-center justify-between gap-2 mb-3">
        <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono flex-shrink-0">
          Achievements
        </h3>
        {streak > 0 && (
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-status-warning/10
                          border border-status-warning/20 flex-shrink-0">
            <Flame className="w-3 h-3 text-status-warning" />
            <span className="text-[10px] font-mono font-bold text-status-warning">
              {streak}д
            </span>
          </div>
        )}
      </div>

      <div className="space-y-2">
        {achievements.map((achievement, index) => {
          const Icon = iconMap[achievement.icon];
          const isCompleted = achievement.completed;

          return (
            <motion.div
              key={achievement.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`p-2.5 rounded-lg border transition-all overflow-hidden
                         ${isCompleted
                           ? 'bg-hud-gradient border-hud-cyan/30 shadow-hud-sm'
                           : 'bg-bg-primary/30 border-border-subtle'
                         }`}
            >
              <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
                                ${isCompleted ? 'bg-hud-cyan/20' : 'bg-bg-tertiary'}`}>
                  <Icon className={`w-4 h-4 ${isCompleted ? 'text-hud-cyan' : 'text-text-muted'}`} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <h4 className={`text-xs font-medium truncate ${isCompleted ? 'text-text-primary' : 'text-text-secondary'}`}>
                      {achievement.title}
                    </h4>
                    {isCompleted && (
                      <span className="text-[8px] font-mono px-1 py-0.5 rounded bg-hud-cyan/20 text-hud-cyan flex-shrink-0">
                        OK
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-text-muted mt-0.5 truncate">{achievement.description}</p>

                  {/* Progress bar */}
                  {!isCompleted && (
                    <div className="mt-1.5">
                      <div className="flex justify-between items-center mb-0.5">
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
                          transition={{ duration: 1, delay: index * 0.1 }}
                          className="h-full bg-hud-gradient rounded-full"
                          style={{
                            boxShadow: '0 0 8px rgba(6, 182, 212, 0.5)',
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

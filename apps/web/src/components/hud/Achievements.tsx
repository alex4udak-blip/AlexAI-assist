import { motion } from 'framer-motion';
import { Trophy, Flame, Zap, Clock, Bot, Target, Check } from 'lucide-react';

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
      transition={{ duration: 0.3 }}
      className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800"
    >
      <div className="flex items-center justify-between gap-2 mb-4">
        <h3 className="text-xs text-zinc-500 font-medium tracking-wide">
          Achievements
        </h3>
        {streak > 0 && (
          <div className="flex items-center gap-1.5 text-amber-500">
            <Flame className="w-3.5 h-3.5" />
            <span className="text-xs font-medium tabular-nums">
              {streak}d streak
            </span>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {achievements.map((achievement, index) => {
          const Icon = iconMap[achievement.icon];
          const isCompleted = achievement.completed;

          return (
            <motion.div
              key={achievement.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: index * 0.05 }}
              className={`p-3 rounded-lg transition-colors ${
                isCompleted
                  ? 'bg-zinc-800/50'
                  : 'bg-zinc-800/20'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  isCompleted ? 'bg-emerald-500/10' : 'bg-zinc-800'
                }`}>
                  <Icon className={`w-4 h-4 ${isCompleted ? 'text-emerald-400' : 'text-zinc-500'}`} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className={`text-sm font-medium truncate ${isCompleted ? 'text-zinc-200' : 'text-zinc-400'}`}>
                      {achievement.title}
                    </h4>
                    {isCompleted && (
                      <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-zinc-500 mt-0.5 truncate">{achievement.description}</p>

                  {/* Progress bar */}
                  {!isCompleted && (
                    <div className="mt-2.5">
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="text-xs text-zinc-500 tabular-nums">
                          {achievement.progress}%
                        </span>
                        {achievement.value && (
                          <span className="text-xs text-zinc-400 tabular-nums">
                            {achievement.value}
                          </span>
                        )}
                      </div>
                      <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${achievement.progress}%` }}
                          transition={{ duration: 0.8, delay: index * 0.1, ease: [0.32, 0.72, 0, 1] }}
                          className="h-full bg-gradient-to-r from-violet-500 to-violet-400 rounded-full"
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

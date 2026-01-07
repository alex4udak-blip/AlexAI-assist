import { motion, AnimatePresence } from 'framer-motion';
import { Bot, CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import { formatRelativeTime } from '../../lib/utils';

interface ActivityItem {
  id: string;
  agentName: string;
  action: string;
  status: 'success' | 'error' | 'pending';
  timestamp: string;
  details?: string;
}

interface AgentActivityStreamProps {
  activities: ActivityItem[];
  maxItems?: number;
}

export function AgentActivityStream({ activities, maxItems = 10 }: AgentActivityStreamProps) {
  const displayActivities = activities.slice(0, maxItems);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-5 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow h-full flex flex-col"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono">
          Agent Activity Stream
        </h3>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 bg-status-success rounded-full animate-pulse" />
          <span className="text-xs font-mono text-status-success">LIVE</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 scrollbar-hide">
        <AnimatePresence mode="popLayout">
          {displayActivities.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full py-8"
            >
              <Clock className="w-8 h-8 text-text-muted mb-2" />
              <p className="text-sm text-text-muted">Ожидание активности агентов...</p>
            </motion.div>
          ) : (
            displayActivities.map((activity, index) => {
              const StatusIcon = activity.status === 'success' ? CheckCircle :
                                activity.status === 'error' ? AlertTriangle : Clock;
              const statusColor = activity.status === 'success' ? 'text-status-success' :
                                 activity.status === 'error' ? 'text-status-error' : 'text-status-warning';

              return (
                <motion.div
                  key={activity.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.02 }}
                  className="flex items-start gap-3 p-3 rounded-lg bg-bg-primary/30
                             border border-transparent hover:border-border-subtle
                             transition-colors group"
                >
                  {/* Agent icon */}
                  <div className="w-8 h-8 rounded-lg bg-hud-cyan/10 flex items-center justify-center
                                  shrink-0 group-hover:bg-hud-cyan/20 transition-colors">
                    <Bot className="w-4 h-4 text-hud-cyan" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-text-primary text-sm">
                        {activity.agentName}
                      </span>
                      <StatusIcon className={`w-3.5 h-3.5 ${statusColor}`} />
                    </div>
                    <p className="text-sm text-text-secondary truncate">
                      {activity.action}
                    </p>
                    {activity.details && (
                      <p className="text-xs text-text-muted mt-0.5 truncate">
                        {activity.details}
                      </p>
                    )}
                  </div>

                  {/* Timestamp */}
                  <span className="text-xs text-text-muted font-mono shrink-0">
                    {formatRelativeTime(activity.timestamp)}
                  </span>
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>

      {/* Gradient fade at bottom */}
      <div className="h-8 bg-gradient-to-t from-bg-secondary/60 to-transparent -mt-8 relative pointer-events-none" />
    </motion.div>
  );
}

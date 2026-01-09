import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle, Info, AlertTriangle, Terminal } from 'lucide-react';
import { useAgentLogs } from '../../hooks/useAgents';
import { formatDateTime, cn } from '../../lib/utils';

interface AgentLogsProps {
  agentId: string;
}

const levelIcons = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: AlertCircle,
};

const levelColors = {
  info: { text: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
  success: { text: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/30' },
  warning: { text: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
  error: { text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' },
};

export function AgentLogs({ agentId }: AgentLogsProps) {
  const { data: logs, loading } = useAgentLogs(agentId);

  if (loading) {
    return (
      <div className="relative p-6 rounded-xl border-2 border-green-500/30
                      bg-gradient-to-br from-black/40 via-black/20 to-transparent
                      backdrop-blur-sm overflow-hidden">
        <div className="relative z-10">
          <h2 className="text-lg font-mono uppercase tracking-wider text-green-400 mb-4 flex items-center gap-2">
            <Terminal className="w-5 h-5" />
            System Logs
          </h2>
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-green-500/5 rounded-lg animate-pulse border border-green-500/10" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative p-6 rounded-xl border-2 border-green-500/30
                    bg-gradient-to-br from-black/60 via-black/40 to-transparent
                    backdrop-blur-sm overflow-hidden shadow-[0_0_20px_rgba(34,197,94,0.2)]">
      {/* Terminal scanlines */}
      <motion.div
        className="absolute left-0 right-0 h-[2px] bg-green-500 opacity-20 blur-[1px]"
        animate={{ top: ['0%', '100%'] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
      />

      {/* Grid pattern */}
      <div className="absolute inset-0 opacity-[0.02]"
           style={{
             backgroundImage: `
               linear-gradient(rgba(34,197,94,0.2) 1px, transparent 1px),
               linear-gradient(90deg, rgba(34,197,94,0.2) 1px, transparent 1px)
             `,
             backgroundSize: '20px 20px'
           }}
      />

      {/* Corner brackets */}
      <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-green-500/50" />
      <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-green-500/50" />
      <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-green-500/50" />
      <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-green-500/50" />

      <div className="relative z-10">
        {/* Terminal header */}
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-green-500/20">
          <Terminal className="w-5 h-5 text-green-400" />
          <h2 className="text-lg font-mono uppercase tracking-wider text-green-400">
            System Logs
          </h2>
          <div className="flex-1" />
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs font-mono text-green-400/60 uppercase tracking-wider">
              Live
            </span>
          </div>
        </div>

        {/* Log entries */}
        {logs && logs.length > 0 ? (
          <div className="space-y-2 max-h-[600px] overflow-auto custom-scrollbar pr-2">
            {logs.map((log, index) => {
              const Icon = levelIcons[log.level as keyof typeof levelIcons] || Info;
              const colors = levelColors[log.level as keyof typeof levelColors] || levelColors.info;

              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`flex items-start gap-3 p-4 rounded-lg border ${colors.border}
                             ${colors.bg} backdrop-blur-sm relative overflow-hidden
                             hover:border-current/50 transition-colors group`}
                >
                  {/* Subtle glow on hover */}
                  <div className={`absolute inset-0 ${colors.bg} opacity-0 group-hover:opacity-50 transition-opacity`} />

                  {/* Icon */}
                  <div className={`relative z-10 ${colors.bg} p-2 rounded-lg border ${colors.border}`}>
                    <Icon className={cn('w-4 h-4 shrink-0', colors.text)} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 relative z-10">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <span className={`text-xs font-mono uppercase tracking-wider ${colors.text}/60`}>
                        {log.level}
                      </span>
                      <span className="text-[10px] text-text-muted font-mono shrink-0">
                        {formatDateTime(log.created_at)}
                      </span>
                    </div>
                    <p className={`text-sm font-mono ${colors.text} leading-relaxed`}>
                      {log.message}
                    </p>
                    {log.data && (
                      <pre className={`mt-3 text-xs font-mono ${colors.text}/80 bg-black/40
                                     p-3 rounded-lg border ${colors.border} overflow-auto
                                     max-h-48 custom-scrollbar`}>
                        {JSON.stringify(log.data, null, 2)}
                      </pre>
                    )}
                  </div>

                  {/* Timeline dot */}
                  <div className={`absolute left-[30px] top-[52px] bottom-[-8px] w-[1px] ${colors.border}
                                  ${index === logs.length - 1 ? 'hidden' : ''}`} />
                </motion.div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-16">
            <Terminal className="w-16 h-16 text-green-400/20 mx-auto mb-4" />
            <p className="text-green-400/40 font-mono text-sm uppercase tracking-wider">
              No logs recorded yet
            </p>
            <p className="text-text-muted/50 font-mono text-xs mt-2">
              Logs will appear here when the agent runs
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

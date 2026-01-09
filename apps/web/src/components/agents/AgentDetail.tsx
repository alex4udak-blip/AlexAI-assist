import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Play, Settings, Code, Activity, Cpu, Clock, AlertTriangle } from 'lucide-react';
import { AgentLogs } from './AgentLogs';
import { formatDateTime, formatDuration } from '../../lib/utils';
import type { Agent } from '../../lib/api';

interface AgentDetailProps {
  agent: Agent;
  onBack: () => void;
  onRun?: (id: string) => void;
  onEdit?: (id: string) => void;
}

export function AgentDetail({ agent, onBack, onRun, onEdit }: AgentDetailProps) {
  const [activeTab, setActiveTab] = useState('overview');

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'logs', label: 'Logs', icon: Code },
    { id: 'code', label: 'Code', icon: Cpu },
  ];

  // Status-based colors
  const statusColors = {
    active: { text: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/50', glow: 'shadow-[0_0_20px_rgba(34,197,94,0.3)]' },
    disabled: { text: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30', glow: 'shadow-[0_0_15px_rgba(59,130,246,0.2)]' },
    draft: { text: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30', glow: 'shadow-[0_0_15px_rgba(249,115,22,0.2)]' },
  };

  const colors = statusColors[agent.status as keyof typeof statusColors] || statusColors.draft;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* HUD Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative"
      >
        <div className={`p-6 rounded-xl border-2 ${colors.border} ${colors.glow}
                        bg-gradient-to-br from-black/60 via-black/40 to-transparent
                        backdrop-blur-sm overflow-hidden`}>
          {/* Grid background */}
          <div className="absolute inset-0 opacity-[0.03]"
               style={{
                 backgroundImage: `
                   linear-gradient(rgba(34,197,94,0.1) 1px, transparent 1px),
                   linear-gradient(90deg, rgba(34,197,94,0.1) 1px, transparent 1px)
                 `,
                 backgroundSize: '20px 20px'
               }}
          />

          {/* Corner brackets */}
          <div className={`absolute top-0 left-0 w-12 h-12 border-t-2 border-l-2 ${colors.border}`} />
          <div className={`absolute top-0 right-0 w-12 h-12 border-t-2 border-r-2 ${colors.border}`} />
          <div className={`absolute bottom-0 left-0 w-12 h-12 border-b-2 border-l-2 ${colors.border}`} />
          <div className={`absolute bottom-0 right-0 w-12 h-12 border-b-2 border-r-2 ${colors.border}`} />

          <div className="relative z-10 flex items-center gap-4">
            <motion.button
              whileHover={{ scale: 1.1, x: -4 }}
              whileTap={{ scale: 0.9 }}
              onClick={onBack}
              className={`p-3 ${colors.text} ${colors.bg} rounded-lg border ${colors.border}
                         hover:bg-white/[0.1] transition-colors`}
            >
              <ArrowLeft className="w-5 h-5" />
            </motion.button>

            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h1 className={`text-3xl font-bold ${colors.text} font-mono uppercase tracking-wider`}>
                  {agent.name}
                </h1>
                {/* Animated status badge */}
                <div className={`px-3 py-1 rounded-lg ${colors.bg} border ${colors.border} relative overflow-hidden`}>
                  <motion.div
                    className={`absolute inset-0 ${colors.bg}`}
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                  <span className={`text-xs font-mono uppercase tracking-widest ${colors.text} relative z-10`}>
                    {agent.status}
                  </span>
                </div>
              </div>
              <p className="text-text-tertiary/80 text-sm font-light">{agent.description}</p>
            </div>

            <div className="flex items-center gap-2">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => onEdit?.(agent.id)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg
                           text-blue-400 bg-blue-500/10 border border-blue-500/30
                           hover:bg-blue-500/20 transition-all font-mono text-sm uppercase tracking-wider"
              >
                <Settings className="w-4 h-4" />
                Edit
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => onRun?.(agent.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg
                           ${colors.text} ${colors.bg} border ${colors.border}
                           hover:border-current/70 transition-all font-mono text-sm uppercase tracking-wider
                           ${colors.glow}`}
              >
                <Play className="w-4 h-4" />
                Run
              </motion.button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* HUD Tabs */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="flex gap-2"
      >
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <motion.button
              key={tab.id}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 rounded-lg font-mono text-sm uppercase tracking-wider
                         transition-all border-2 ${
                isActive
                  ? `${colors.text} ${colors.bg} ${colors.border} ${colors.glow}`
                  : 'text-text-muted bg-white/[0.02] border-white/[0.05] hover:border-white/[0.15]'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </motion.button>
          );
        })}
      </motion.div>

      {/* Content Panels */}
      {activeTab === 'overview' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          {/* Statistics HUD Panel */}
          <div className={`relative p-6 rounded-xl border-2 ${colors.border}
                          bg-gradient-to-br from-black/40 via-black/20 to-transparent
                          backdrop-blur-sm overflow-hidden`}>
            {/* Scan line effect */}
            <motion.div
              className={`absolute left-0 right-0 h-[1px] bg-green-500 opacity-20`}
              animate={{ top: ['0%', '100%'] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
            />

            <div className="relative z-10">
              <h2 className={`text-lg font-mono uppercase tracking-wider ${colors.text} mb-6 flex items-center gap-2`}>
                <Activity className="w-5 h-5" />
                Statistics
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div className={`p-4 rounded-lg ${colors.bg} border ${colors.border}`}>
                  <p className={`text-[10px] ${colors.text}/60 mb-2 uppercase tracking-widest font-mono`}>Total Runs</p>
                  <p className={`text-3xl font-bold ${colors.text} font-mono`}>{agent.run_count}</p>
                </div>
                <div className={`p-4 rounded-lg bg-green-500/10 border border-green-500/30`}>
                  <p className={`text-[10px] text-green-400/60 mb-2 uppercase tracking-widest font-mono`}>Success Rate</p>
                  <p className={`text-3xl font-bold text-green-400 font-mono`}>
                    {agent.run_count > 0
                      ? ((agent.success_count / agent.run_count) * 100).toFixed(0)
                      : 0}%
                  </p>
                </div>
                <div className={`p-4 rounded-lg ${colors.bg} border ${colors.border}`}>
                  <p className={`text-[10px] ${colors.text}/60 mb-2 uppercase tracking-widest font-mono`}>Time Saved</p>
                  <p className={`text-3xl font-bold ${colors.text} font-mono`}>
                    {formatDuration(agent.total_time_saved_seconds)}
                  </p>
                </div>
                <div className={`p-4 rounded-lg bg-orange-500/10 border border-orange-500/30`}>
                  <p className={`text-[10px] text-orange-400/60 mb-2 uppercase tracking-widest font-mono`}>Errors</p>
                  <p className={`text-3xl font-bold text-orange-400 font-mono`}>{agent.error_count}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Configuration HUD Panel */}
          <div className={`relative p-6 rounded-xl border-2 ${colors.border}
                          bg-gradient-to-br from-black/40 via-black/20 to-transparent
                          backdrop-blur-sm overflow-hidden`}>
            {/* Circuit pattern */}
            <div className="absolute inset-0 opacity-[0.02]"
                 style={{
                   backgroundImage: `
                     linear-gradient(rgba(34,197,94,0.1) 1px, transparent 1px),
                     linear-gradient(90deg, rgba(34,197,94,0.1) 1px, transparent 1px)
                   `,
                   backgroundSize: '15px 15px'
                 }}
            />

            <div className="relative z-10">
              <h2 className={`text-lg font-mono uppercase tracking-wider ${colors.text} mb-6 flex items-center gap-2`}>
                <Cpu className="w-5 h-5" />
                Configuration
              </h2>
              <dl className="space-y-4">
                <div className={`p-3 rounded-lg ${colors.bg} border ${colors.border}`}>
                  <dt className={`text-[10px] ${colors.text}/60 mb-1 uppercase tracking-widest font-mono`}>Type</dt>
                  <dd className={`${colors.text} font-mono`}>{agent.agent_type}</dd>
                </div>
                <div className={`p-3 rounded-lg ${colors.bg} border ${colors.border}`}>
                  <dt className={`text-[10px] ${colors.text}/60 mb-1 uppercase tracking-widest font-mono flex items-center gap-1`}>
                    <Clock className="w-3 h-3" />
                    Created
                  </dt>
                  <dd className={`${colors.text} font-mono text-sm`}>
                    {formatDateTime(agent.created_at)}
                  </dd>
                </div>
                {agent.last_run_at && (
                  <div className={`p-3 rounded-lg ${colors.bg} border ${colors.border}`}>
                    <dt className={`text-[10px] ${colors.text}/60 mb-1 uppercase tracking-widest font-mono flex items-center gap-1`}>
                      <Activity className="w-3 h-3" />
                      Last Run
                    </dt>
                    <dd className={`${colors.text} font-mono text-sm`}>
                      {formatDateTime(agent.last_run_at)}
                    </dd>
                  </div>
                )}
                {agent.last_error && (
                  <div className={`p-3 rounded-lg bg-orange-500/10 border border-orange-500/30`}>
                    <dt className={`text-[10px] text-orange-400/60 mb-1 uppercase tracking-widest font-mono flex items-center gap-1`}>
                      <AlertTriangle className="w-3 h-3" />
                      Last Error
                    </dt>
                    <dd className={`text-orange-400 text-sm font-mono`}>
                      {agent.last_error}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        </motion.div>
      )}

      {activeTab === 'logs' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <AgentLogs agentId={agent.id} />
        </motion.div>
      )}

      {activeTab === 'code' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`relative p-6 rounded-xl border-2 ${colors.border}
                      bg-gradient-to-br from-black/40 via-black/20 to-transparent
                      backdrop-blur-sm overflow-hidden`}
        >
          <div className="relative z-10">
            <h2 className={`text-lg font-mono uppercase tracking-wider ${colors.text} mb-4 flex items-center gap-2`}>
              <Code className="w-5 h-5" />
              Agent Code
            </h2>
            {agent.code ? (
              <div className="relative">
                <pre className="bg-black/60 p-6 rounded-lg overflow-auto text-sm font-mono text-green-400/90
                               border border-green-500/20 shadow-[0_0_20px_rgba(34,197,94,0.1)]
                               max-h-96 custom-scrollbar">
                  {agent.code}
                </pre>
              </div>
            ) : (
              <div className="text-center py-12">
                <Code className="w-12 h-12 text-text-muted mx-auto mb-3 opacity-30" />
                <p className="text-text-muted font-mono text-sm uppercase tracking-wider">
                  No custom code defined
                </p>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}

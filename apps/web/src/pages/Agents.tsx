import { useState, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Plus, Bot } from 'lucide-react';
import { AgentCard } from '../components/agents/AgentCard';
import { AgentDetail } from '../components/agents/AgentDetail';
import { CreateAgentModal } from '../components/agents/CreateAgentModal';
import {
  useAgents,
  useCreateAgent,
  useUpdateAgent,
  useRunAgent,
  useEnableAgent,
  useDisableAgent,
  useDeleteAgent,
} from '../hooks/useAgents';

type FilterStatus = 'all' | 'active' | 'disabled' | 'draft';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function Agents() {
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterStatus>('all');

  const { data: agents, loading, refetch } = useAgents();
  const { mutate: createAgent, loading: creating } = useCreateAgent();
  const { mutate: updateAgent, loading: updating } = useUpdateAgent();
  const { mutate: runAgent } = useRunAgent();
  const { mutate: enableAgent } = useEnableAgent();
  const { mutate: disableAgent } = useDisableAgent();
  const { mutate: deleteAgent } = useDeleteAgent();

  const filteredAgents = useMemo(() => {
    return agents?.filter((agent) => {
      if (filter === 'all') return true;
      return agent.status === filter;
    });
  }, [agents, filter]);

  const handleCreate = useCallback(async (data: {
    name: string;
    description: string;
    agent_type: string;
    trigger_type: string;
    trigger_value: string;
  }) => {
    await createAgent({
      name: data.name,
      description: data.description,
      agent_type: data.agent_type,
      trigger_config: {
        type: data.trigger_type,
        value: data.trigger_value,
      },
      actions: [],
    });
    setShowCreateModal(false);
    refetch();
  }, [createAgent, refetch]);

  const handleEdit = useCallback(async (data: {
    name: string;
    description: string;
    agent_type: string;
    trigger_type: string;
    trigger_value: string;
  }) => {
    if (!editingAgentId) return;
    await updateAgent(editingAgentId, {
      name: data.name,
      description: data.description,
      agent_type: data.agent_type,
      trigger_config: {
        type: data.trigger_type,
        value: data.trigger_value,
      },
    });
    setShowEditModal(false);
    setEditingAgentId(null);
    refetch();
  }, [editingAgentId, updateAgent, refetch]);

  const openEditModal = useCallback((id: string) => {
    setEditingAgentId(id);
    setShowEditModal(true);
  }, []);

  const handleRun = useCallback(async (id: string) => {
    await runAgent(id);
    refetch();
  }, [runAgent, refetch]);

  const handleEnable = useCallback(async (id: string) => {
    await enableAgent(id);
    refetch();
  }, [enableAgent, refetch]);

  const handleDisable = useCallback(async (id: string) => {
    await disableAgent(id);
    refetch();
  }, [disableAgent, refetch]);

  const handleDelete = useCallback(async (id: string) => {
    if (confirm('Вы уверены, что хотите удалить этого агента?')) {
      await deleteAgent(id);
      if (selectedAgentId === id) {
        setSelectedAgentId(null);
      }
      refetch();
    }
  }, [deleteAgent, selectedAgentId, refetch]);

  const selectedAgent = agents?.find((a) => a.id === selectedAgentId);
  const editingAgent = agents?.find((a) => a.id === editingAgentId);

  if (selectedAgent) {
    return (
      <>
        <AgentDetail
          agent={selectedAgent}
          onBack={() => setSelectedAgentId(null)}
          onRun={handleRun}
          onEdit={openEditModal}
        />
        <CreateAgentModal
          isOpen={showEditModal}
          onClose={() => {
            setShowEditModal(false);
            setEditingAgentId(null);
          }}
          onCreate={handleEdit}
          loading={updating}
          initialData={editingAgent}
          isEdit={true}
        />
      </>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        {/* Filter tabs - HUD style */}
        <div className="flex gap-2 p-1.5 rounded-lg bg-black/40 border border-green-500/20 backdrop-blur-sm w-fit">
          {(['all', 'active', 'disabled', 'draft'] as FilterStatus[]).map((status) => {
            const isActive = filter === status;
            return (
              <motion.button
                key={status}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setFilter(status)}
                className={`px-4 py-2 text-xs font-mono uppercase tracking-wider rounded-md transition-all duration-150
                           border ${
                  isActive
                    ? 'bg-green-500/20 text-green-400 border-green-500/50 shadow-[0_0_10px_rgba(34,197,94,0.2)]'
                    : 'text-text-tertiary border-transparent hover:text-text-secondary hover:bg-white/[0.05] hover:border-white/[0.1]'
                }`}
              >
                {status === 'all' ? 'All' :
                 status === 'active' ? 'Active' :
                 status === 'disabled' ? 'Disabled' : 'Draft'}
              </motion.button>
            );
          })}
        </div>

        {/* Create button - Neon style */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg
                     bg-gradient-to-r from-green-500/20 to-green-400/20 text-green-400
                     border-2 border-green-500/50 font-mono text-sm uppercase tracking-wider
                     hover:border-green-400 hover:shadow-[0_0_20px_rgba(34,197,94,0.4)]
                     transition-all relative overflow-hidden group"
        >
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-green-500/10 to-green-400/10"
            animate={{
              opacity: [0.5, 1, 0.5],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
          <Plus className="w-4 h-4 relative z-10" />
          <span className="relative z-10">New Agent</span>
        </motion.button>
      </motion.div>

      {/* Agents Grid */}
      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="p-5 rounded-xl border-2 border-green-500/20 bg-black/20 backdrop-blur-sm relative overflow-hidden">
              <motion.div
                className="absolute left-0 right-0 h-[2px] bg-green-500 opacity-20"
                animate={{ top: ['0%', '100%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear', delay: i * 0.2 }}
              />
              <div className="flex items-start gap-4 mb-4">
                <div className="w-12 h-12 rounded-lg bg-green-500/10 animate-pulse" />
                <div className="flex-1">
                  <div className="h-5 w-32 bg-green-500/10 rounded animate-pulse mb-2" />
                  <div className="h-4 w-48 bg-green-500/10 rounded animate-pulse" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 mb-4">
                {[...Array(3)].map((_, j) => (
                  <div key={j} className="p-3 rounded-lg bg-green-500/5 border border-green-500/10 animate-pulse">
                    <div className="h-3 w-16 bg-green-500/10 rounded mb-2" />
                    <div className="h-6 w-12 bg-green-500/10 rounded" />
                  </div>
                ))}
              </div>
              <div className="h-8 w-full bg-green-500/10 rounded animate-pulse" />
            </div>
          ))}
        </div>
      ) : filteredAgents && filteredAgents.length > 0 ? (
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          {filteredAgents.map((agent) => (
            <motion.div
              key={agent.id}
              variants={item}
              onClick={() => setSelectedAgentId(agent.id)}
              className="cursor-pointer"
            >
              <AgentCard
                agent={agent}
                onRun={() => handleRun(agent.id)}
                onEnable={() => handleEnable(agent.id)}
                onDisable={() => handleDisable(agent.id)}
                onDelete={() => handleDelete(agent.id)}
              />
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative p-16 rounded-xl border-2 border-green-500/20
                     bg-gradient-to-br from-black/60 via-black/40 to-transparent
                     backdrop-blur-sm overflow-hidden text-center"
        >
          {/* Circuit pattern background */}
          <div className="absolute inset-0 opacity-[0.03]"
               style={{
                 backgroundImage: `
                   linear-gradient(rgba(34,197,94,0.3) 2px, transparent 2px),
                   linear-gradient(90deg, rgba(34,197,94,0.3) 2px, transparent 2px),
                   linear-gradient(rgba(34,197,94,0.2) 1px, transparent 1px),
                   linear-gradient(90deg, rgba(34,197,94,0.2) 1px, transparent 1px)
                 `,
                 backgroundSize: '50px 50px, 50px 50px, 10px 10px, 10px 10px',
                 backgroundPosition: '-2px -2px, -2px -2px, -1px -1px, -1px -1px'
               }}
          />

          {/* Animated scan lines */}
          <motion.div
            className="absolute left-0 right-0 h-[2px] bg-green-500 opacity-20 blur-sm"
            animate={{ top: ['0%', '100%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          />

          {/* Corner brackets */}
          <div className="absolute top-0 left-0 w-16 h-16 border-t-2 border-l-2 border-green-500/50" />
          <div className="absolute top-0 right-0 w-16 h-16 border-t-2 border-r-2 border-green-500/50" />
          <div className="absolute bottom-0 left-0 w-16 h-16 border-b-2 border-l-2 border-green-500/50" />
          <div className="absolute bottom-0 right-0 w-16 h-16 border-b-2 border-r-2 border-green-500/50" />

          <div className="relative z-10">
            <motion.div
              animate={{
                opacity: [0.3, 0.6, 0.3],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            >
              <Bot className="w-20 h-20 text-green-400/40 mx-auto mb-6" />
            </motion.div>
            <h3 className="text-xl font-mono uppercase tracking-wider text-green-400 mb-3">
              {filter === 'all' ? 'No Agents Found' : 'No Agents with This Status'}
            </h3>
            <p className="text-text-tertiary/60 text-sm mb-8 max-w-md mx-auto font-light leading-relaxed">
              Create your first agent to automate routine tasks.
              Agents can send notifications, run scripts, and much more.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg
                         bg-gradient-to-r from-green-500/20 to-green-400/20 text-green-400
                         border-2 border-green-500/50 font-mono text-sm uppercase tracking-wider
                         hover:border-green-400 hover:shadow-[0_0_20px_rgba(34,197,94,0.4)]
                         transition-all relative overflow-hidden"
            >
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-green-500/10 to-green-400/10"
                animate={{
                  opacity: [0.5, 1, 0.5],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              />
              <Plus className="w-4 h-4 relative z-10" />
              <span className="relative z-10">Create Agent</span>
            </motion.button>
          </div>
        </motion.div>
      )}

      <CreateAgentModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreate}
        loading={creating}
      />
    </div>
  );
}

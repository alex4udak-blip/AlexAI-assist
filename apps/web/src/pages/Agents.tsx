import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Bot } from 'lucide-react';
import { AgentCard } from '../components/agents/AgentCard';
import { AgentDetail } from '../components/agents/AgentDetail';
import { CreateAgentModal } from '../components/agents/CreateAgentModal';
import {
  useAgents,
  useCreateAgent,
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
  const [filter, setFilter] = useState<FilterStatus>('all');

  const { data: agents, loading, refetch } = useAgents();
  const { mutate: createAgent, loading: creating } = useCreateAgent();
  const { mutate: runAgent } = useRunAgent();
  const { mutate: enableAgent } = useEnableAgent();
  const { mutate: disableAgent } = useDisableAgent();
  const { mutate: deleteAgent } = useDeleteAgent();

  const selectedAgent = agents?.find((a) => a.id === selectedAgentId);

  const filteredAgents = agents?.filter((agent) => {
    if (filter === 'all') return true;
    return agent.status === filter;
  });

  const handleCreate = async (data: {
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
  };

  const handleRun = async (id: string) => {
    await runAgent(id);
    refetch();
  };

  const handleEnable = async (id: string) => {
    await enableAgent(id);
    refetch();
  };

  const handleDisable = async (id: string) => {
    await disableAgent(id);
    refetch();
  };

  const handleDelete = async (id: string) => {
    if (confirm('Вы уверены, что хотите удалить этого агента?')) {
      await deleteAgent(id);
      if (selectedAgentId === id) {
        setSelectedAgentId(null);
      }
      refetch();
    }
  };

  if (selectedAgent) {
    return (
      <AgentDetail
        agent={selectedAgent}
        onBack={() => setSelectedAgentId(null)}
        onRun={handleRun}
        onEdit={() => {}}
      />
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Filter tabs */}
        <div className="flex gap-1 p-1 rounded-lg bg-white/[0.03] w-fit">
          {(['all', 'active', 'disabled', 'draft'] as FilterStatus[]).map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-150
                         ${filter === status
                           ? 'bg-white/[0.08] text-text-primary'
                           : 'text-text-tertiary hover:text-text-secondary hover:bg-white/[0.03]'
                         }`}
            >
              {status === 'all' ? 'Все' :
               status === 'active' ? 'Активные' :
               status === 'disabled' ? 'Отключены' : 'Черновики'}
            </button>
          ))}
        </div>

        {/* Create button */}
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg
                     bg-accent-gradient text-white text-sm font-medium
                     hover:opacity-90 hover:shadow-glow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          Создать агента
        </button>
      </div>

      {/* Agents Grid */}
      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="p-5 rounded-2xl border border-border-subtle bg-surface-primary">
              <div className="flex items-start gap-4 mb-4">
                <div className="w-12 h-12 rounded-xl skeleton" />
                <div className="flex-1">
                  <div className="h-5 w-32 skeleton mb-2" />
                  <div className="h-4 w-48 skeleton" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 mb-4">
                {[...Array(3)].map((_, j) => (
                  <div key={j} className="p-3 rounded-xl bg-white/[0.02]">
                    <div className="h-3 w-16 skeleton mb-2" />
                    <div className="h-6 w-12 skeleton" />
                  </div>
                ))}
              </div>
              <div className="h-8 w-full skeleton" />
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
          className="p-12 rounded-2xl border border-border-subtle bg-surface-primary text-center"
        >
          <Bot className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            {filter === 'all' ? 'Пока нет агентов' : 'Нет агентов с таким статусом'}
          </h3>
          <p className="text-text-tertiary text-sm mb-6 max-w-md mx-auto">
            Создайте своего первого агента для автоматизации рутинных задач.
            Агенты могут отправлять уведомления, запускать скрипты и многое другое.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg
                       bg-accent-gradient text-white text-sm font-medium
                       hover:opacity-90 hover:shadow-glow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            Создать агента
          </button>
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

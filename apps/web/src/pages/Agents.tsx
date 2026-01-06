import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '../components/ui/Button';
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

export default function Agents() {
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { data: agents, loading, refetch } = useAgents();
  const { mutate: createAgent, loading: creating } = useCreateAgent();
  const { mutate: runAgent } = useRunAgent();
  const { mutate: enableAgent } = useEnableAgent();
  const { mutate: disableAgent } = useDisableAgent();
  const { mutate: deleteAgent } = useDeleteAgent();

  const selectedAgent = agents?.find((a) => a.id === selectedAgentId);

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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Агенты</h1>
          <p className="text-text-tertiary mt-1">
            Управляйте своими агентами автоматизации
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4" />
          Создать агента
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-48 skeleton rounded-xl" />
          ))}
        </div>
      ) : agents && agents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {agents.map((agent) => (
            <div
              key={agent.id}
              onClick={() => setSelectedAgentId(agent.id)}
              className="cursor-pointer"
            >
              <AgentCard
                agent={agent}
                onRun={(e) => {
                  e?.stopPropagation?.();
                  handleRun(agent.id);
                }}
                onEnable={(e) => {
                  e?.stopPropagation?.();
                  handleEnable(agent.id);
                }}
                onDisable={(e) => {
                  e?.stopPropagation?.();
                  handleDisable(agent.id);
                }}
                onDelete={(e) => {
                  e?.stopPropagation?.();
                  handleDelete(agent.id);
                }}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-bg-secondary border border-border-subtle rounded-xl p-12 text-center">
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Пока нет агентов
          </h3>
          <p className="text-text-tertiary mb-4">
            Создайте своего первого агента для автоматизации рутинных задач
          </p>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4" />
            Создать агента
          </Button>
        </div>
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

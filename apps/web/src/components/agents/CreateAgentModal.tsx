import { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Input, Textarea } from '../ui/Input';
import { Select } from '../ui/Select';
import { Button } from '../ui/Button';

interface CreateAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: AgentFormData) => void;
  loading?: boolean;
}

interface AgentFormData {
  name: string;
  description: string;
  agent_type: string;
  trigger_type: string;
  trigger_value: string;
}

const agentTypes = [
  { value: 'monitor', label: 'Monitor' },
  { value: 'reporter', label: 'Reporter' },
  { value: 'assistant', label: 'Assistant' },
  { value: 'automation', label: 'Automation' },
];

const triggerTypes = [
  { value: 'schedule', label: 'Schedule (cron)' },
  { value: 'event', label: 'Event-based' },
  { value: 'pattern', label: 'Pattern match' },
  { value: 'webhook', label: 'Webhook' },
];

export function CreateAgentModal({
  isOpen,
  onClose,
  onCreate,
  loading,
}: CreateAgentModalProps) {
  const [formData, setFormData] = useState<AgentFormData>({
    name: '',
    description: '',
    agent_type: 'automation',
    trigger_type: 'schedule',
    trigger_value: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate(formData);
  };

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Agent" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Name"
          name="name"
          value={formData.name}
          onChange={handleChange}
          placeholder="My Agent"
          required
        />

        <Textarea
          label="Description"
          name="description"
          value={formData.description}
          onChange={handleChange}
          placeholder="What does this agent do?"
          rows={3}
        />

        <Select
          label="Agent Type"
          name="agent_type"
          value={formData.agent_type}
          onChange={handleChange}
          options={agentTypes}
        />

        <Select
          label="Trigger Type"
          name="trigger_type"
          value={formData.trigger_type}
          onChange={handleChange}
          options={triggerTypes}
        />

        <Input
          label="Trigger Value"
          name="trigger_value"
          value={formData.trigger_value}
          onChange={handleChange}
          placeholder={
            formData.trigger_type === 'schedule'
              ? '0 9 * * * (every day at 9 AM)'
              : 'Enter trigger condition'
          }
        />

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create Agent
          </Button>
        </div>
      </form>
    </Modal>
  );
}

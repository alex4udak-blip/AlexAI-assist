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
  { value: 'monitor', label: 'Мониторинг' },
  { value: 'reporter', label: 'Репортер' },
  { value: 'assistant', label: 'Ассистент' },
  { value: 'automation', label: 'Автоматизация' },
];

const triggerTypes = [
  { value: 'schedule', label: 'Расписание (cron)' },
  { value: 'event', label: 'По событию' },
  { value: 'pattern', label: 'По паттерну' },
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
    <Modal isOpen={isOpen} onClose={onClose} title="Создать агента" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Название"
          name="name"
          value={formData.name}
          onChange={handleChange}
          placeholder="Мой агент"
          required
        />

        <Textarea
          label="Описание"
          name="description"
          value={formData.description}
          onChange={handleChange}
          placeholder="Что делает этот агент?"
          rows={3}
        />

        <Select
          label="Тип агента"
          name="agent_type"
          value={formData.agent_type}
          onChange={handleChange}
          options={agentTypes}
        />

        <Select
          label="Тип триггера"
          name="trigger_type"
          value={formData.trigger_type}
          onChange={handleChange}
          options={triggerTypes}
        />

        <Input
          label="Значение триггера"
          name="trigger_value"
          value={formData.trigger_value}
          onChange={handleChange}
          placeholder={
            formData.trigger_type === 'schedule'
              ? '0 9 * * * (каждый день в 9:00)'
              : 'Введите условие триггера'
          }
        />

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" loading={loading}>
            Создать агента
          </Button>
        </div>
      </form>
    </Modal>
  );
}

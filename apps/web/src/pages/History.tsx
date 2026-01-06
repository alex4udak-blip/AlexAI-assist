import { useState } from 'react';
import { Calendar, Filter } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { useTimeline } from '../hooks/useAnalytics';
import { formatDateTime, truncate } from '../lib/utils';

const categoryOptions = [
  { value: '', label: 'Все категории' },
  { value: 'coding', label: 'Программирование' },
  { value: 'browsing', label: 'Браузинг' },
  { value: 'writing', label: 'Письмо' },
  { value: 'communication', label: 'Коммуникация' },
];

export default function History() {
  const [hours, setHours] = useState(24);
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');

  const { data: events, loading } = useTimeline(hours);

  const filteredEvents = events?.filter((event) => {
    if (category && event.category !== category) return false;
    if (search) {
      const searchLower = search.toLowerCase();
      return (
        event.app_name?.toLowerCase().includes(searchLower) ||
        event.window_title?.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">История</h1>
        <p className="text-text-tertiary mt-1">
          Просмотр истории активности
        </p>
      </div>

      <div className="flex flex-wrap gap-4">
        <Input
          placeholder="Поиск событий..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64"
        />
        <Select
          options={categoryOptions}
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-40"
        />
        <Select
          options={[
            { value: '24', label: 'Последние 24 часа' },
            { value: '48', label: 'Последние 48 часов' },
            { value: '72', label: 'Последние 72 часа' },
            { value: '168', label: 'Последняя неделя' },
          ]}
          value={hours.toString()}
          onChange={(e) => setHours(parseInt(e.target.value))}
          className="w-40"
        />
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="h-16 skeleton rounded-lg" />
          ))}
        </div>
      ) : filteredEvents && filteredEvents.length > 0 ? (
        <Card className="p-0 overflow-hidden">
          <div className="divide-y divide-border-subtle">
            {filteredEvents.map((event) => (
              <div
                key={event.id}
                className="flex items-center gap-4 p-4 hover:bg-bg-hover transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-text-primary">
                      {event.app_name || 'Неизвестное приложение'}
                    </p>
                    {event.category && (
                      <Badge variant="default">{event.category}</Badge>
                    )}
                  </div>
                  <p className="text-sm text-text-tertiary truncate">
                    {truncate(event.window_title || '', 80)}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm text-text-secondary">
                    {formatDateTime(event.timestamp)}
                  </p>
                  <p className="text-xs text-text-muted">{event.event_type}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <Card className="p-12 text-center">
          <Calendar className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            События не найдены
          </h3>
          <p className="text-text-tertiary">
            {search || category
              ? 'Попробуйте изменить фильтры'
              : 'Активность появится здесь, когда сборщик начнёт отправлять данные'}
          </p>
        </Card>
      )}
    </div>
  );
}

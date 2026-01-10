import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { truncate } from '../../lib/utils';
import { Smartphone, Circle, Clock } from 'lucide-react';

export interface DeviceStatus {
  device_id: string;
  connected: boolean;
  active_app: string | null;
  queue_size: number;
  permissions: {
    accessibility: boolean;
    screen_recording: boolean;
  };
  last_seen?: string;
  sync_status?: {
    last_sync_at: string | null;
    events_since_sync: number;
    sync_status: 'connected' | 'disconnected';
  };
}

interface DeviceCardProps {
  device: DeviceStatus;
  selected?: boolean;
  onClick?: () => void;
}

export function DeviceCard({ device, selected, onClick }: DeviceCardProps) {
  const getTimeSinceSync = (lastSync: string | null): string => {
    if (!lastSync) return 'Никогда';
    const secondsAgo = Math.floor(
      (Date.now() - new Date(lastSync).getTime()) / 1000
    );
    if (secondsAgo < 60) return `${secondsAgo} сек. назад`;
    const minutesAgo = Math.floor(secondsAgo / 60);
    if (minutesAgo < 60) return `${minutesAgo} мин. назад`;
    const hoursAgo = Math.floor(minutesAgo / 60);
    return `${hoursAgo} ч. назад`;
  };

  const getSyncStatusColor = (lastSync: string | null): string => {
    if (!lastSync) return 'text-status-error';
    const secondsAgo = Math.floor(
      (Date.now() - new Date(lastSync).getTime()) / 1000
    );
    if (secondsAgo < 60) return 'text-status-success';
    if (secondsAgo < 300) return 'text-status-warning';
    return 'text-status-error';
  };

  return (
    <Card
      variant={selected ? 'elevated' : 'interactive'}
      className={`cursor-pointer transition-all ${
        selected ? 'ring-1 ring-accent-primary' : ''
      }`}
      onClick={onClick}
    >
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-accent-muted">
            <Smartphone className="w-4 h-4 text-accent-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base">
              {truncate(device.device_id, 20)}
            </CardTitle>
            <div className="flex items-center gap-2 mt-1">
              <Circle
                className={`w-2 h-2 fill-current ${
                  device.connected ? 'text-status-success' : 'text-status-error'
                }`}
              />
              <span className="text-xs text-text-tertiary">
                {device.connected ? 'Подключено' : 'Отключено'}
              </span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Active App */}
        <div>
          <span className="text-xs text-text-tertiary">Активное приложение</span>
          <p className="text-sm text-text-secondary mt-0.5">
            {device.active_app || 'Нет'}
          </p>
        </div>

        {/* Queue Size */}
        <div>
          <span className="text-xs text-text-tertiary">Размер очереди</span>
          <p className="text-sm text-text-secondary mt-0.5">
            {device.queue_size} команд
          </p>
        </div>

        {/* Sync Status */}
        {device.sync_status && (
          <div>
            <span className="text-xs text-text-tertiary">Последняя синхронизация</span>
            <div className="flex items-center gap-2 mt-0.5">
              <Clock
                className={`w-3 h-3 ${getSyncStatusColor(
                  device.sync_status.last_sync_at
                )}`}
              />
              <p className="text-sm text-text-secondary">
                {getTimeSinceSync(device.sync_status.last_sync_at)}
              </p>
              {device.sync_status.events_since_sync > 0 && (
                <Badge variant="warning" className="text-xs">
                  {device.sync_status.events_since_sync} ожидает
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Permissions */}
        <div>
          <span className="text-xs text-text-tertiary mb-1.5 block">
            Разрешения
          </span>
          <div className="flex flex-wrap gap-1.5">
            <Badge
              variant={device.permissions.accessibility ? 'success' : 'error'}
            >
              Доступность
            </Badge>
            <Badge
              variant={device.permissions.screen_recording ? 'success' : 'error'}
            >
              Запись экрана
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

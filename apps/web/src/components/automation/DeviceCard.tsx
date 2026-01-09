import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { truncate } from '../../lib/utils';
import { Smartphone, Circle } from 'lucide-react';

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
}

interface DeviceCardProps {
  device: DeviceStatus;
  selected?: boolean;
  onClick?: () => void;
}

export function DeviceCard({ device, selected, onClick }: DeviceCardProps) {
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
                {device.connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Active App */}
        <div>
          <span className="text-xs text-text-tertiary">Active App</span>
          <p className="text-sm text-text-secondary mt-0.5">
            {device.active_app || 'None'}
          </p>
        </div>

        {/* Queue Size */}
        <div>
          <span className="text-xs text-text-tertiary">Queue Size</span>
          <p className="text-sm text-text-secondary mt-0.5">
            {device.queue_size} commands
          </p>
        </div>

        {/* Permissions */}
        <div>
          <span className="text-xs text-text-tertiary mb-1.5 block">
            Permissions
          </span>
          <div className="flex flex-wrap gap-1.5">
            <Badge
              variant={device.permissions.accessibility ? 'success' : 'error'}
            >
              Accessibility
            </Badge>
            <Badge
              variant={device.permissions.screen_recording ? 'success' : 'error'}
            >
              Screen Recording
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

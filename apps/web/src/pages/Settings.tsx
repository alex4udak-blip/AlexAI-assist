import { useState } from 'react';
import { Save, Trash2, RefreshCw } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Switch } from '../components/ui/Switch';
import { Select } from '../components/ui/Select';
import { Button } from '../components/ui/Button';

export default function Settings() {
  const [settings, setSettings] = useState({
    notifications: true,
    autoStart: true,
    syncInterval: '30',
    theme: 'dark',
    dataRetention: '30',
  });

  const handleSave = () => {
    // Save settings to localStorage or API
    localStorage.setItem('observer-settings', JSON.stringify(settings));
  };

  const handleClearData = () => {
    if (
      confirm(
        'Are you sure you want to clear all local data? This cannot be undone.'
      )
    ) {
      localStorage.clear();
      window.location.reload();
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="text-text-tertiary mt-1">
          Configure Observer preferences
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>General</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <Switch
            label="Enable notifications"
            checked={settings.notifications}
            onChange={(checked) =>
              setSettings((s) => ({ ...s, notifications: checked }))
            }
          />

          <Switch
            label="Start on system boot"
            checked={settings.autoStart}
            onChange={(checked) =>
              setSettings((s) => ({ ...s, autoStart: checked }))
            }
          />

          <Select
            label="Sync interval"
            options={[
              { value: '10', label: 'Every 10 seconds' },
              { value: '30', label: 'Every 30 seconds' },
              { value: '60', label: 'Every minute' },
              { value: '300', label: 'Every 5 minutes' },
            ]}
            value={settings.syncInterval}
            onChange={(e) =>
              setSettings((s) => ({ ...s, syncInterval: e.target.value }))
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Data & Privacy</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <Select
            label="Data retention period"
            options={[
              { value: '7', label: '7 days' },
              { value: '30', label: '30 days' },
              { value: '90', label: '90 days' },
              { value: '365', label: '1 year' },
            ]}
            value={settings.dataRetention}
            onChange={(e) =>
              setSettings((s) => ({ ...s, dataRetention: e.target.value }))
            }
          />

          <div className="pt-4 border-t border-border-subtle">
            <h4 className="text-sm font-medium text-text-primary mb-2">
              Danger Zone
            </h4>
            <p className="text-sm text-text-tertiary mb-4">
              Clear all local data including settings and cached information.
            </p>
            <Button variant="danger" onClick={handleClearData}>
              <Trash2 className="w-4 h-4" />
              Clear Local Data
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Connection</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            label="Server URL"
            value={import.meta.env.VITE_API_URL || 'http://localhost:8000'}
            disabled
          />

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-status-success rounded-full" />
              <span className="text-sm text-text-secondary">Connected</span>
            </div>
            <Button variant="ghost" size="sm">
              <RefreshCw className="w-4 h-4" />
              Test Connection
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave}>
          <Save className="w-4 h-4" />
          Save Settings
        </Button>
      </div>
    </div>
  );
}

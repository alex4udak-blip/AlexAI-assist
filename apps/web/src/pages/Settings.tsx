import { useState, useEffect } from 'react';
import { Save, Trash2, RefreshCw } from 'lucide-react';
import { config } from '../lib/config';
import { secureStorage, StorageValidator } from '../lib/secureStorage';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Switch } from '../components/ui/Switch';
import { Select } from '../components/ui/Select';
import { Button } from '../components/ui/Button';

interface SettingsData {
  notifications: boolean;
  autoStart: boolean;
  syncInterval: string;
  theme: string;
  dataRetention: string;
}

const DEFAULT_SETTINGS: SettingsData = {
  notifications: true,
  autoStart: true,
  syncInterval: '30',
  theme: 'dark',
  dataRetention: '30',
};

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData>(DEFAULT_SETTINGS);

  // Load settings on mount
  useEffect(() => {
    try {
      const stored = secureStorage.getItem<SettingsData>('observer-settings');

      if (stored && StorageValidator.validateSettings(stored)) {
        setSettings(stored);
      } else {
        // If validation fails, clear invalid data
        secureStorage.removeItem('observer-settings');
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  }, []);

  const handleSave = () => {
    try {
      // Validate before saving
      if (!StorageValidator.validateSettings(settings)) {
        console.error('Invalid settings data');
        return;
      }

      // Save using secure storage (not encrypted as it's non-sensitive preference data)
      secureStorage.setItem('observer-settings', settings, {
        type: 'local',
        encrypt: false
      });

      // TODO: Also sync to API for cross-device settings
    } catch (err) {
      console.error('Failed to save settings:', err);
    }
  };

  const handleClearData = () => {
    if (
      confirm(
        'Вы уверены, что хотите очистить все локальные данные? Это действие нельзя отменить.'
      )
    ) {
      try {
        // Clear both local and session storage
        secureStorage.clear('local');
        secureStorage.clear('session');
      } catch (err) {
        console.error('Failed to clear storage:', err);
      }
      window.location.reload();
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Настройки</h1>
        <p className="text-text-tertiary mt-1">
          Настройте параметры Observer
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Общие</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <Switch
            label="Включить уведомления"
            checked={settings.notifications}
            onChange={(checked) =>
              setSettings((s) => ({ ...s, notifications: checked }))
            }
          />

          <Switch
            label="Запускать при загрузке системы"
            checked={settings.autoStart}
            onChange={(checked) =>
              setSettings((s) => ({ ...s, autoStart: checked }))
            }
          />

          <Select
            label="Интервал синхронизации"
            options={[
              { value: '10', label: 'Каждые 10 секунд' },
              { value: '30', label: 'Каждые 30 секунд' },
              { value: '60', label: 'Каждую минуту' },
              { value: '300', label: 'Каждые 5 минут' },
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
          <CardTitle>Данные и конфиденциальность</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <Select
            label="Срок хранения данных"
            options={[
              { value: '7', label: '7 дней' },
              { value: '30', label: '30 дней' },
              { value: '90', label: '90 дней' },
              { value: '365', label: '1 год' },
            ]}
            value={settings.dataRetention}
            onChange={(e) =>
              setSettings((s) => ({ ...s, dataRetention: e.target.value }))
            }
          />

          <div className="pt-4 border-t border-border-subtle">
            <h4 className="text-sm font-medium text-text-primary mb-2">
              Опасная зона
            </h4>
            <p className="text-sm text-text-tertiary mb-4">
              Очистить все локальные данные, включая настройки и кэшированную информацию.
            </p>
            <Button variant="danger" onClick={handleClearData} aria-label="Очистить локальные данные">
              <Trash2 className="w-4 h-4" />
              Очистить локальные данные
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Подключение</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            label="URL сервера"
            value={config.apiUrl}
            disabled
          />

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-status-success rounded-full" />
              <span className="text-sm text-text-secondary">Подключено</span>
            </div>
            <Button variant="ghost" size="sm" aria-label="Проверить подключение к серверу">
              <RefreshCw className="w-4 h-4" />
              Проверить подключение
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} aria-label="Сохранить настройки">
          <Save className="w-4 h-4" />
          Сохранить настройки
        </Button>
      </div>
    </div>
  );
}

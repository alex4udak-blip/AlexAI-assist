import { useState, useEffect } from 'react';
import { Save, Trash2, RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { config } from '../lib/config';
import { api } from '../lib/api';
import { secureStorage, StorageValidator } from '../lib/secureStorage';
import { getDeviceId } from '../lib/utils';
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
  const [connectionStatus, setConnectionStatus] = useState<'unknown' | 'checking' | 'healthy' | 'degraded' | 'unhealthy'>('unknown');
  const [connectionDetails, setConnectionDetails] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // Load settings on mount - prefer server as source of truth
  useEffect(() => {
    const loadSettings = async () => {
      setIsLoading(true);
      try {
        const deviceId = getDeviceId();

        // Try to load from server first
        try {
          const serverSettings = await api.getSettings(deviceId);

          if (serverSettings.settings && Object.keys(serverSettings.settings).length > 0) {
            // Validate server settings
            if (StorageValidator.validateSettings(serverSettings.settings)) {
              setSettings(serverSettings.settings as SettingsData);
              // Also update local storage to match server
              secureStorage.setItem('observer-settings', serverSettings.settings, {
                type: 'local',
                encrypt: false
              });
              return;
            }
          }
        } catch (serverErr) {
          console.warn('Failed to load settings from server, falling back to local:', serverErr);
        }

        // Fallback to local storage if server fails or has no settings
        const stored = secureStorage.getItem<SettingsData>('observer-settings');
        if (stored && StorageValidator.validateSettings(stored)) {
          setSettings(stored);
        } else {
          // If validation fails, clear invalid data
          secureStorage.removeItem('observer-settings');
        }
      } catch (err) {
        console.error('Failed to load settings:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadSettings();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Validate before saving
      if (!StorageValidator.validateSettings(settings)) {
        console.error('Invalid settings data');
        alert('Некорректные данные настроек');
        return;
      }

      const deviceId = getDeviceId();

      // Save to local storage first
      secureStorage.setItem('observer-settings', settings, {
        type: 'local',
        encrypt: false
      });

      // Sync to server
      try {
        await api.saveSettings(deviceId, settings);
        console.log('Settings saved to server successfully');
      } catch (serverErr) {
        console.error('Failed to save settings to server:', serverErr);
        alert('Настройки сохранены локально, но не удалось синхронизировать с сервером');
      }
    } catch (err) {
      console.error('Failed to save settings:', err);
      alert('Не удалось сохранить настройки');
    } finally {
      setIsSaving(false);
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

  const handleCheckConnection = async () => {
    setConnectionStatus('checking');
    setConnectionDetails('');

    try {
      const health = await api.checkHealth();
      setConnectionStatus(health.status);

      const details: string[] = [];
      if (health.checks.database.status === 'healthy') {
        details.push(`БД: ${health.checks.database.latency_ms}мс`);
      } else {
        details.push(`БД: ${health.checks.database.error || 'ошибка'}`);
      }

      if (health.checks.redis.status === 'healthy') {
        details.push(`Redis: ${health.checks.redis.latency_ms}мс`);
      }

      setConnectionDetails(details.join(', '));
    } catch (err) {
      setConnectionStatus('unhealthy');
      setConnectionDetails(err instanceof Error ? err.message : 'Не удалось подключиться к серверу');
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

          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                {connectionStatus === 'unknown' && (
                  <>
                    <span className="w-2 h-2 bg-text-muted rounded-full" />
                    <span className="text-sm text-text-secondary">Не проверено</span>
                  </>
                )}
                {connectionStatus === 'checking' && (
                  <>
                    <RefreshCw className="w-4 h-4 text-text-muted animate-spin" />
                    <span className="text-sm text-text-secondary">Проверка...</span>
                  </>
                )}
                {connectionStatus === 'healthy' && (
                  <>
                    <CheckCircle className="w-4 h-4 text-status-success" />
                    <span className="text-sm text-status-success">Подключено</span>
                  </>
                )}
                {connectionStatus === 'degraded' && (
                  <>
                    <AlertCircle className="w-4 h-4 text-status-warning" />
                    <span className="text-sm text-status-warning">Ограниченная работа</span>
                  </>
                )}
                {connectionStatus === 'unhealthy' && (
                  <>
                    <XCircle className="w-4 h-4 text-status-error" />
                    <span className="text-sm text-status-error">Отключено</span>
                  </>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCheckConnection}
                disabled={connectionStatus === 'checking'}
                aria-label="Проверить подключение к серверу"
              >
                <RefreshCw className={`w-4 h-4 ${connectionStatus === 'checking' ? 'animate-spin' : ''}`} />
                Проверить подключение
              </Button>
            </div>
            {connectionDetails && (
              <p className="text-xs text-text-tertiary">{connectionDetails}</p>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button
          onClick={handleSave}
          disabled={isLoading || isSaving}
          aria-label="Сохранить настройки"
        >
          <Save className="w-4 h-4" />
          {isSaving ? 'Сохранение...' : 'Сохранить настройки'}
        </Button>
      </div>
    </div>
  );
}

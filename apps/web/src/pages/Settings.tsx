import { useState } from 'react';
import { Save, Trash2, RefreshCw } from 'lucide-react';
import { config } from '../lib/config';
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
        'Вы уверены, что хотите очистить все локальные данные? Это действие нельзя отменить.'
      )
    ) {
      localStorage.clear();
      window.location.reload();
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
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
            <Button variant="danger" onClick={handleClearData}>
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
            <Button variant="ghost" size="sm">
              <RefreshCw className="w-4 h-4" />
              Проверить подключение
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave}>
          <Save className="w-4 h-4" />
          Сохранить настройки
        </Button>
      </div>
    </div>
  );
}

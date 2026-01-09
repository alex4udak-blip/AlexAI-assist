import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Server,
  Shield,
  Clock,
  CheckCircle,
  XCircle,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';

interface SettingsData {
  apiUrl: string;
  syncInterval: number;
  launchAtStartup: boolean;
}

interface Permissions {
  accessibility: boolean;
  screenRecording: boolean;
}

interface Props {
  onBack: () => void;
}

export default function Settings({ onBack }: Props) {
  const [settings, setSettings] = useState<SettingsData>({
    apiUrl: '',
    syncInterval: 30,
    launchAtStartup: false,
  });
  const [permissions, setPermissions] = useState<Permissions>({
    accessibility: false,
    screenRecording: false,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadSettings();
    checkPermissions();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await invoke<SettingsData>('get_settings');
      setSettings(data);
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
  };

  const checkPermissions = async () => {
    try {
      const perms = await invoke<{ accessibility: boolean; screen_recording: boolean }>('check_all_permissions');
      setPermissions({
        accessibility: perms.accessibility,
        screenRecording: perms.screen_recording,
      });
    } catch (e) {
      console.error('Failed to check permissions:', e);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      await invoke('save_settings', { settings });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error('Failed to save settings:', e);
    } finally {
      setSaving(false);
    }
  };

  const requestPermission = async (type: string) => {
    try {
      await invoke('request_permission', { permission: type });
      // Recheck after a delay
      setTimeout(checkPermissions, 1000);
    } catch (e) {
      console.error('Failed to request permission:', e);
    }
  };

  const openSystemPreferences = async (pane: string) => {
    try {
      await invoke('open_system_preferences', { pane });
    } catch (e) {
      console.error('Failed to open system preferences:', e);
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col">
      {/* Header */}
      <div
        data-tauri-drag-region
        className="h-12 bg-bg-secondary/80 backdrop-blur-xl border-b border-border-subtle flex items-center px-4 shrink-0"
      >
        <div className="w-20" />
        <div className="flex-1 flex items-center justify-center">
          <span className="text-sm font-medium text-text-secondary">Настройки</span>
        </div>
        <div className="w-20 flex justify-end">
          <button
            onClick={onBack}
            className="p-1.5 text-text-tertiary hover:text-text-primary hover:bg-bg-hover rounded-md transition-colors"
            title="Назад"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Server Connection */}
          <section className="bg-bg-secondary rounded-xl p-5 border border-border-subtle">
            <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Server className="w-4 h-4 text-violet-400" />
              Сервер
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-text-muted mb-2">API URL</label>
                <input
                  type="url"
                  value={settings.apiUrl}
                  onChange={(e) => setSettings({ ...settings, apiUrl: e.target.value })}
                  placeholder="https://your-server.railway.app"
                  className="w-full px-3 py-2 bg-bg-tertiary border border-border-subtle rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-violet-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-2">
                  Интервал синхронизации (секунды)
                </label>
                <input
                  type="number"
                  min="10"
                  max="300"
                  value={settings.syncInterval}
                  onChange={(e) => setSettings({ ...settings, syncInterval: parseInt(e.target.value) || 30 })}
                  className="w-24 px-3 py-2 bg-bg-tertiary border border-border-subtle rounded-lg text-sm text-text-primary focus:outline-none focus:border-violet-500 transition-colors"
                />
              </div>
            </div>
          </section>

          {/* Permissions */}
          <section className="bg-bg-secondary rounded-xl p-5 border border-border-subtle">
            <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Shield className="w-4 h-4 text-violet-400" />
              Доступы
            </h2>
            <div className="space-y-3">
              {/* Accessibility */}
              <div className="flex items-center justify-between p-3 bg-bg-tertiary rounded-lg">
                <div className="flex items-center gap-3">
                  {permissions.accessibility ? (
                    <CheckCircle className="w-5 h-5 text-status-success" />
                  ) : (
                    <XCircle className="w-5 h-5 text-status-error" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-text-primary">Accessibility</p>
                    <p className="text-xs text-text-muted">Отслеживание окон и приложений</p>
                  </div>
                </div>
                {!permissions.accessibility && (
                  <button
                    onClick={() => requestPermission('accessibility')}
                    className="px-3 py-1.5 text-xs font-medium text-violet-400 hover:text-violet-300 hover:bg-violet-500/10 rounded-md transition-colors"
                  >
                    Разрешить
                  </button>
                )}
              </div>

              {/* Screen Recording */}
              <div className="flex items-center justify-between p-3 bg-bg-tertiary rounded-lg">
                <div className="flex items-center gap-3">
                  {permissions.screenRecording ? (
                    <CheckCircle className="w-5 h-5 text-status-success" />
                  ) : (
                    <XCircle className="w-5 h-5 text-status-error" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-text-primary">Screen Recording</p>
                    <p className="text-xs text-text-muted">Захват экрана для OCR</p>
                  </div>
                </div>
                {!permissions.screenRecording && (
                  <button
                    onClick={() => requestPermission('screen_recording')}
                    className="px-3 py-1.5 text-xs font-medium text-violet-400 hover:text-violet-300 hover:bg-violet-500/10 rounded-md transition-colors"
                  >
                    Разрешить
                  </button>
                )}
              </div>

              {/* Open System Preferences */}
              <button
                onClick={() => openSystemPreferences('privacy')}
                className="w-full mt-2 py-2 text-xs text-text-muted hover:text-text-secondary flex items-center justify-center gap-1 transition-colors"
              >
                <ExternalLink className="w-3 h-3" />
                Открыть Системные настройки
              </button>
            </div>
          </section>

          {/* Startup */}
          <section className="bg-bg-secondary rounded-xl p-5 border border-border-subtle">
            <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4 text-violet-400" />
              Запуск
            </h2>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.launchAtStartup}
                onChange={(e) => setSettings({ ...settings, launchAtStartup: e.target.checked })}
                className="w-4 h-4 rounded border-border-subtle bg-bg-tertiary text-violet-500 focus:ring-violet-500 focus:ring-offset-0"
              />
              <span className="text-sm text-text-secondary">Запускать при входе в систему</span>
            </label>
          </section>

          {/* Save Button */}
          <button
            onClick={saveSettings}
            disabled={saving}
            className="w-full py-3 bg-gradient-to-r from-violet-500 to-violet-600 text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {saving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Сохранение...
              </>
            ) : saved ? (
              <>
                <CheckCircle className="w-4 h-4" />
                Сохранено
              </>
            ) : (
              'Сохранить настройки'
            )}
          </button>
        </div>
      </main>
    </div>
  );
}

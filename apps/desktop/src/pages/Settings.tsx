import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Server,
  Shield,
  Clock,
  Check,
  X,
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
    <div className="h-full flex flex-col bg-[#2d2d2d] rounded-xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="px-4 py-3 bg-[#252525] flex items-center justify-between">
        <button
          onClick={onBack}
          className="p-1.5 -ml-1.5 rounded-md hover:bg-white/5 text-white/50 hover:text-white/80 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <span className="text-[13px] text-white/90 font-medium">Настройки</span>
        <div className="w-7" />
      </div>

      {/* Content - scrollable */}
      <div className="flex-1 overflow-y-auto">
        {/* Server section */}
        <div className="px-4 py-3 border-b border-white/5">
          <div className="flex items-center gap-2 mb-3">
            <Server className="w-3.5 h-3.5 text-white/40" />
            <span className="text-[10px] text-white/40 uppercase tracking-wider">Сервер</span>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-[11px] text-white/50 mb-1.5">API URL</label>
              <input
                type="url"
                value={settings.apiUrl}
                onChange={(e) => setSettings({ ...settings, apiUrl: e.target.value })}
                placeholder="https://server.railway.app"
                className="w-full px-2.5 py-1.5 bg-[#1a1a1a] border border-white/10 rounded-md text-[12px] text-white/90 placeholder-white/30 focus:outline-none focus:border-white/20 transition-colors"
              />
            </div>
            <div>
              <label className="block text-[11px] text-white/50 mb-1.5">Интервал синхр. (сек)</label>
              <input
                type="number"
                min="10"
                max="300"
                value={settings.syncInterval}
                onChange={(e) => setSettings({ ...settings, syncInterval: parseInt(e.target.value) || 30 })}
                className="w-20 px-2.5 py-1.5 bg-[#1a1a1a] border border-white/10 rounded-md text-[12px] text-white/90 focus:outline-none focus:border-white/20 transition-colors"
              />
            </div>
          </div>
        </div>

        {/* Permissions section */}
        <div className="px-4 py-3 border-b border-white/5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Shield className="w-3.5 h-3.5 text-white/40" />
              <span className="text-[10px] text-white/40 uppercase tracking-wider">Доступы</span>
            </div>
            <button
              onClick={checkPermissions}
              className="p-1 rounded hover:bg-white/5 text-white/40 hover:text-white/60 transition-colors"
              title="Обновить статус"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>
          <div className="space-y-2">
            <PermissionRow
              name="Accessibility"
              description="Отслеживание окон"
              granted={permissions.accessibility}
              onRequest={() => requestPermission('accessibility')}
            />
            <PermissionRow
              name="Screen Recording"
              description="Захват экрана"
              granted={permissions.screenRecording}
              onRequest={() => requestPermission('screen_recording')}
            />
            <button
              onClick={() => openSystemPreferences('privacy')}
              className="w-full mt-1 py-1.5 text-[11px] text-white/40 hover:text-white/60 flex items-center justify-center gap-1 transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
              Системные настройки
            </button>
          </div>
        </div>

        {/* Startup section */}
        <div className="px-4 py-3 border-b border-white/5">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-3.5 h-3.5 text-white/40" />
            <span className="text-[10px] text-white/40 uppercase tracking-wider">Запуск</span>
          </div>
          <label className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.launchAtStartup}
              onChange={(e) => setSettings({ ...settings, launchAtStartup: e.target.checked })}
              className="w-3.5 h-3.5 rounded border-white/20 bg-[#1a1a1a] text-blue-500 focus:ring-0 focus:ring-offset-0"
            />
            <span className="text-[12px] text-white/70">Запускать при входе</span>
          </label>
        </div>
      </div>

      {/* Save button */}
      <div className="px-4 py-3 bg-[#252525] border-t border-white/5">
        <button
          onClick={saveSettings}
          disabled={saving}
          className="w-full py-2 bg-white/10 hover:bg-white/15 text-white/90 text-[12px] font-medium rounded-md transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
        >
          {saving ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              Сохранение...
            </>
          ) : saved ? (
            <>
              <Check className="w-3.5 h-3.5" />
              Сохранено
            </>
          ) : (
            'Сохранить'
          )}
        </button>
      </div>
    </div>
  );
}

interface PermissionRowProps {
  name: string;
  description: string;
  granted: boolean;
  onRequest: () => void;
}

function PermissionRow({ name, description, granted, onRequest }: PermissionRowProps) {
  return (
    <div className="flex items-center justify-between py-1.5 px-2 rounded-md bg-[#1a1a1a]">
      <div className="flex items-center gap-2">
        {granted ? (
          <Check className="w-3.5 h-3.5 text-green-400" />
        ) : (
          <X className="w-3.5 h-3.5 text-red-400" />
        )}
        <div>
          <p className="text-[12px] text-white/80">{name}</p>
          <p className="text-[10px] text-white/40">{description}</p>
        </div>
      </div>
      {!granted && (
        <button
          onClick={onRequest}
          className="px-2 py-1 text-[10px] text-blue-400 hover:bg-blue-500/10 rounded transition-colors"
        >
          Разрешить
        </button>
      )}
    </div>
  );
}

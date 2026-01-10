import { useState, useEffect } from 'react';
import { Activity, Pause, Play, Settings, ExternalLink, RefreshCw, X, Minus } from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';
import { getCurrentWindow } from '@tauri-apps/api/window';

interface Stats {
  eventsToday: number;
  lastSync: string;
  status: 'collecting' | 'paused' | 'syncing';
}

interface Props {
  onOpenSettings: () => void;
}

export default function MenuBar({ onOpenSettings }: Props) {
  const [stats, setStats] = useState<Stats>({
    eventsToday: 0,
    lastSync: 'Никогда',
    status: 'collecting',
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const result = await invoke<Stats>('get_stats');
        setStats(result);
      } catch (e) {
        console.error('Failed to fetch stats:', e);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const toggleCollection = async () => {
    try {
      await invoke('toggle_collection');
      setStats((prev) => ({
        ...prev,
        status: prev.status === 'collecting' ? 'paused' : 'collecting',
      }));
    } catch (e) {
      console.error('Failed to toggle collection:', e);
    }
  };

  const openDashboard = async () => {
    try {
      await invoke('open_dashboard');
    } catch (e) {
      console.error('Failed to open dashboard:', e);
    }
  };

  const syncNow = async () => {
    try {
      setStats((prev) => ({ ...prev, status: 'syncing' }));
      await invoke('sync_now');
      setStats((prev) => ({ ...prev, status: 'collecting', lastSync: 'Только что' }));
    } catch (e) {
      console.error('Failed to sync:', e);
      setStats((prev) => ({ ...prev, status: 'collecting' }));
    }
  };

  const statusColors = {
    collecting: 'bg-status-success',
    paused: 'bg-status-warning',
    syncing: 'bg-status-info',
  };

  const hideWindow = async () => {
    // Notify backend that window is hidden (for tray icon sync)
    await invoke('set_window_visible', { visible: false });
    const window = getCurrentWindow();
    await window.hide();
  };

  const minimizeWindow = async () => {
    const window = getCurrentWindow();
    await window.minimize();
  };

  return (
    <div className="w-80 bg-bg-secondary rounded-xl border border-border-default shadow-lg overflow-hidden">
      {/* Draggable Header */}
      <div
        className="px-4 py-3 bg-bg-tertiary border-b border-border-subtle cursor-move"
        data-tauri-drag-region
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2" data-tauri-drag-region>
            <div className="w-8 h-8 rounded-lg bg-accent-gradient flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <div data-tauri-drag-region>
              <h1 className="text-sm font-semibold text-text-primary">Observer</h1>
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${statusColors[stats.status]}`} />
                <span className="text-xs text-text-tertiary capitalize">{stats.status === 'collecting' ? 'Сбор' : stats.status === 'paused' ? 'Пауза' : 'Синхронизация'}</span>
              </div>
            </div>
          </div>
          {/* Window controls */}
          <div className="flex items-center gap-1">
            <button
              onClick={minimizeWindow}
              className="w-6 h-6 rounded-md flex items-center justify-center text-text-muted hover:text-text-secondary hover:bg-bg-hover transition-colors"
              title="Свернуть"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={hideWindow}
              className="w-6 h-6 rounded-md flex items-center justify-center text-text-muted hover:text-white hover:bg-red-500/80 transition-colors"
              title="Закрыть"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="p-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-bg-tertiary rounded-lg p-3">
            <p className="text-xs text-text-muted">Событий сегодня</p>
            <p className="text-xl font-bold text-text-primary">{stats.eventsToday}</p>
          </div>
          <div className="bg-bg-tertiary rounded-lg p-3">
            <p className="text-xs text-text-muted">Последняя синхр.</p>
            <p className="text-sm font-medium text-text-primary">{stats.lastSync}</p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 pb-4 space-y-2">
        <button
          onClick={toggleCollection}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
        >
          {stats.status === 'collecting' ? (
            <>
              <Pause className="w-4 h-4" />
              Приостановить сбор
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Возобновить сбор
            </>
          )}
        </button>

        <button
          onClick={syncNow}
          disabled={stats.status === 'syncing'}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${stats.status === 'syncing' ? 'animate-spin' : ''}`} />
          Синхронизировать
        </button>

        <button
          onClick={openDashboard}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          Открыть дашборд
        </button>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 bg-bg-tertiary border-t border-border-subtle">
        <div className="flex items-center justify-between text-xs text-text-muted">
          <span>v{__APP_VERSION__}</span>
          <button
            onClick={onOpenSettings}
            className="hover:text-text-secondary transition-colors"
            title="Настройки"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

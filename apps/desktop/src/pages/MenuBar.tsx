import { useState, useEffect } from 'react';
import {
  Pause,
  Play,
  RefreshCw,
  ExternalLink,
  Settings,
  Power,
  ChevronRight,
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';
import { getCurrentWindow } from '@tauri-apps/api/window';

interface Stats {
  eventsToday: number;
  lastSync: string;
  status: 'collecting' | 'paused' | 'syncing';
  topApps: { name: string; count: number }[];
}

interface Props {
  onOpenSettings: () => void;
}

export default function MenuBar({ onOpenSettings }: Props) {
  const [stats, setStats] = useState<Stats>({
    eventsToday: 0,
    lastSync: 'Никогда',
    status: 'collecting',
    topApps: [],
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const result = await invoke<Stats>('get_detailed_stats');
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

  const openDashboard = async () => {
    try {
      await invoke('open_dashboard');
      hideWindow();
    } catch (e) {
      console.error('Failed to open dashboard:', e);
    }
  };

  const hideWindow = async () => {
    await invoke('set_window_visible', { visible: false });
    const window = getCurrentWindow();
    await window.hide();
  };

  const quitApp = async () => {
    try {
      const window = getCurrentWindow();
      await window.close();
    } catch (e) {
      console.error('Failed to quit:', e);
    }
  };

  const statusText = stats.status === 'collecting'
    ? 'Сбор активен'
    : stats.status === 'paused'
    ? 'Приостановлен'
    : 'Синхронизация...';

  const statusColor = stats.status === 'collecting'
    ? 'bg-green-500'
    : stats.status === 'paused'
    ? 'bg-amber-500'
    : 'bg-blue-500';

  return (
    <div className="h-full flex flex-col bg-[#2d2d2d] rounded-xl overflow-hidden shadow-2xl">
      {/* Header - compact status bar */}
      <div className="px-4 py-3 bg-[#252525] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className={`w-2 h-2 rounded-full ${statusColor} ${stats.status === 'syncing' ? 'animate-pulse' : ''}`} />
          <span className="text-[13px] text-white/90 font-medium">{statusText}</span>
        </div>
        <span className="text-[11px] text-white/40">{stats.eventsToday.toLocaleString()} событий</span>
      </div>

      {/* Stats section */}
      <div className="px-4 py-3 bg-[#282828]">
        <div className="flex justify-between items-center">
          <div>
            <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Синхронизация</p>
            <p className="text-[13px] text-white/80">{stats.lastSync}</p>
          </div>
          <button
            onClick={syncNow}
            disabled={stats.status === 'syncing'}
            className="p-2 rounded-lg hover:bg-white/5 text-white/50 hover:text-white/80 transition-colors disabled:opacity-40"
            title="Синхронизировать"
          >
            <RefreshCw className={`w-4 h-4 ${stats.status === 'syncing' ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Top Apps - scrollable */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <p className="text-[10px] text-white/40 uppercase tracking-wider mb-2">Топ приложений</p>
        {stats.topApps.length > 0 ? (
          <div className="space-y-1">
            {stats.topApps.slice(0, 6).map((app, i) => (
              <div
                key={app.name}
                className="flex items-center gap-2 py-1.5 px-2 rounded-md hover:bg-white/5 transition-colors"
              >
                <span className="text-[11px] text-white/30 w-4">{i + 1}</span>
                <span className="text-[13px] text-white/80 flex-1 truncate">{app.name}</span>
                <span className="text-[12px] text-white/40 tabular-nums">{app.count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[12px] text-white/30 text-center py-4">Нет данных</p>
        )}
      </div>

      {/* Actions menu */}
      <div className="border-t border-white/5">
        <MenuItem
          icon={stats.status === 'collecting' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          label={stats.status === 'collecting' ? 'Приостановить' : 'Возобновить'}
          onClick={toggleCollection}
        />
        <MenuItem
          icon={<ExternalLink className="w-4 h-4" />}
          label="Открыть веб-дашборд"
          onClick={openDashboard}
          showArrow
        />
        <div className="h-px bg-white/5 mx-3" />
        <MenuItem
          icon={<Settings className="w-4 h-4" />}
          label="Настройки..."
          onClick={onOpenSettings}
        />
        <MenuItem
          icon={<Power className="w-4 h-4" />}
          label="Выйти из Observer"
          onClick={quitApp}
          danger
        />
      </div>

      {/* Version footer */}
      <div className="px-4 py-2 bg-[#252525] border-t border-white/5">
        <span className="text-[10px] text-white/25">Observer v{__APP_VERSION__}</span>
      </div>
    </div>
  );
}

interface MenuItemProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  showArrow?: boolean;
  danger?: boolean;
}

function MenuItem({ icon, label, onClick, disabled, showArrow, danger }: MenuItemProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        w-full flex items-center gap-3 px-4 py-2.5 text-left
        transition-colors disabled:opacity-40 disabled:cursor-not-allowed
        ${danger
          ? 'text-red-400 hover:bg-red-500/10'
          : 'text-white/80 hover:bg-white/5'
        }
      `}
    >
      <span className={danger ? 'text-red-400/60' : 'text-white/40'}>{icon}</span>
      <span className="flex-1 text-[13px]">{label}</span>
      {showArrow && <ChevronRight className="w-3.5 h-3.5 text-white/25" />}
    </button>
  );
}

import { useState, useEffect } from 'react';
import { Activity, Pause, Play, Settings, ExternalLink, RefreshCw } from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';

interface Stats {
  eventsToday: number;
  lastSync: string;
  status: 'collecting' | 'paused' | 'syncing';
}

export default function MenuBar() {
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

  return (
    <div className="w-80 bg-bg-secondary rounded-xl border border-border-default shadow-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-bg-tertiary border-b border-border-subtle">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-accent-gradient flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-text-primary">Observer</h1>
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${statusColors[stats.status]}`} />
                <span className="text-xs text-text-tertiary capitalize">{stats.status === 'collecting' ? 'Сбор' : stats.status === 'paused' ? 'Пауза' : 'Синхронизация'}</span>
              </div>
            </div>
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
          <span>v0.1.0</span>
          <button className="hover:text-text-secondary transition-colors">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

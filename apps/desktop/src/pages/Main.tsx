import { useState, useEffect } from 'react';
import {
  Activity,
  Settings,
  ExternalLink,
  Pause,
  Play,
  RefreshCw,
  Clock,
  Monitor,
  BarChart3,
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';

interface Stats {
  eventsToday: number;
  lastSync: string;
  status: 'collecting' | 'paused' | 'syncing';
  topApps: { name: string; count: number }[];
  activeTime: number;
}

export default function Main() {
  const [stats, setStats] = useState<Stats>({
    eventsToday: 0,
    lastSync: 'Никогда',
    status: 'collecting',
    topApps: [],
    activeTime: 0,
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

  const openDashboard = async () => {
    try {
      await invoke('open_dashboard');
    } catch (e) {
      console.error('Failed to open dashboard:', e);
    }
  };

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Header */}
      <header className="bg-bg-secondary border-b border-border-subtle p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-gradient flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-text-primary">Observer</h1>
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    stats.status === 'collecting'
                      ? 'bg-status-success'
                      : stats.status === 'syncing'
                      ? 'bg-status-info animate-pulse'
                      : 'bg-status-warning'
                  }`}
                />
                <span className="text-xs text-text-tertiary capitalize">
                  {stats.status === 'collecting' ? 'Сбор' : stats.status === 'paused' ? 'Пауза' : 'Синхронизация'}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleCollection}
              className="p-2 text-text-secondary hover:text-text-primary hover:bg-bg-hover rounded-lg transition-colors"
            >
              {stats.status === 'collecting' ? (
                <Pause className="w-5 h-5" />
              ) : (
                <Play className="w-5 h-5" />
              )}
            </button>
            <button className="p-2 text-text-secondary hover:text-text-primary hover:bg-bg-hover rounded-lg transition-colors">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="p-4 space-y-4">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-bg-secondary rounded-xl p-4 border border-border-subtle">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-4 h-4 text-text-tertiary" />
              <span className="text-xs text-text-muted">Событий сегодня</span>
            </div>
            <p className="text-2xl font-bold text-text-primary">
              {stats.eventsToday}
            </p>
          </div>
          <div className="bg-bg-secondary rounded-xl p-4 border border-border-subtle">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-text-tertiary" />
              <span className="text-xs text-text-muted">Активное время</span>
            </div>
            <p className="text-2xl font-bold text-text-primary">
              {formatTime(stats.activeTime)}
            </p>
          </div>
        </div>

        {/* Top Apps */}
        <div className="bg-bg-secondary rounded-xl p-4 border border-border-subtle">
          <h2 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Monitor className="w-4 h-4" />
            Топ приложений
          </h2>
          {stats.topApps.length > 0 ? (
            <div className="space-y-2">
              {stats.topApps.slice(0, 5).map((app) => (
                <div
                  key={app.name}
                  className="flex items-center justify-between"
                >
                  <span className="text-sm text-text-secondary">{app.name}</span>
                  <span className="text-sm font-medium text-text-primary">
                    {app.count}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted text-center py-4">
              Активность ещё не записана
            </p>
          )}
        </div>

        {/* Sync Status */}
        <div className="bg-bg-secondary rounded-xl p-4 border border-border-subtle">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-text-secondary">Последняя синхр.</span>
            <span className="text-sm text-text-primary">{stats.lastSync}</span>
          </div>
          <button
            onClick={() => invoke('sync_now')}
            disabled={stats.status === 'syncing'}
            className="w-full py-2 bg-bg-tertiary hover:bg-bg-hover text-text-secondary text-sm rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${stats.status === 'syncing' ? 'animate-spin' : ''}`}
            />
            {stats.status === 'syncing' ? 'Синхронизация...' : 'Синхронизировать'}
          </button>
        </div>

        {/* Open Dashboard */}
        <button
          onClick={openDashboard}
          className="w-full py-3 bg-accent-gradient text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
        >
          <ExternalLink className="w-4 h-4" />
          Открыть веб-дашборд
        </button>
      </main>
    </div>
  );
}

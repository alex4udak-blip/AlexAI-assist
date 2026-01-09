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
  Eye,
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
    <div className="min-h-screen bg-bg-primary flex flex-col">
      {/* macOS Style Titlebar - draggable area */}
      <div
        data-tauri-drag-region
        className="h-12 bg-bg-secondary/80 backdrop-blur-xl border-b border-border-subtle flex items-center px-4 shrink-0"
      >
        {/* Traffic lights space (macOS native buttons) */}
        <div className="w-20" />

        {/* Center - App title with icon */}
        <div className="flex-1 flex items-center justify-center gap-2">
          <Eye className="w-4 h-4 text-violet-400" />
          <span className="text-sm font-medium text-text-secondary">Observer</span>
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              stats.status === 'collecting'
                ? 'bg-status-success'
                : stats.status === 'syncing'
                ? 'bg-status-info animate-pulse'
                : 'bg-status-warning'
            }`}
          />
        </div>

        {/* Right side actions */}
        <div className="w-20 flex items-center justify-end gap-1">
          <button
            onClick={toggleCollection}
            className="p-1.5 text-text-tertiary hover:text-text-primary hover:bg-bg-hover rounded-md transition-colors"
          >
            {stats.status === 'collecting' ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>
          <button className="p-1.5 text-text-tertiary hover:text-text-primary hover:bg-bg-hover rounded-md transition-colors">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Header */}
      <header className="bg-bg-secondary border-b border-border-subtle p-4 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-400 to-violet-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Eye className="w-5 h-5 text-white" />
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
                  {stats.status === 'collecting' ? 'Сбор данных' : stats.status === 'paused' ? 'Пауза' : 'Синхронизация'}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={openDashboard}
            className="px-4 py-2 bg-gradient-to-r from-violet-500 to-violet-600 text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-violet-500/20"
          >
            <ExternalLink className="w-4 h-4" />
            Веб-дашборд
          </button>
        </div>
      </header>

      {/* Content - scrollable area */}
      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-bg-secondary rounded-xl p-4 border border-border-subtle hover:border-violet-500/30 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-violet-400" />
                <span className="text-xs text-text-muted">Событий сегодня</span>
              </div>
              <p className="text-2xl font-bold text-text-primary">
                {stats.eventsToday.toLocaleString()}
              </p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-4 border border-border-subtle hover:border-violet-500/30 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-violet-400" />
                <span className="text-xs text-text-muted">Активное время</span>
              </div>
              <p className="text-2xl font-bold text-text-primary">
                {formatTime(stats.activeTime)}
              </p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-4 border border-border-subtle hover:border-violet-500/30 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-violet-400" />
                <span className="text-xs text-text-muted">Приложений</span>
              </div>
              <p className="text-2xl font-bold text-text-primary">
                {stats.topApps.length}
              </p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-4 border border-border-subtle hover:border-violet-500/30 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <RefreshCw className="w-4 h-4 text-violet-400" />
                <span className="text-xs text-text-muted">Синхр.</span>
              </div>
              <p className="text-lg font-medium text-text-primary truncate">
                {stats.lastSync}
              </p>
            </div>
          </div>

          {/* Two column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Apps */}
            <div className="bg-bg-secondary rounded-xl p-5 border border-border-subtle">
              <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Monitor className="w-4 h-4 text-violet-400" />
                Топ приложений
              </h2>
              {stats.topApps.length > 0 ? (
                <div className="space-y-3">
                  {stats.topApps.slice(0, 8).map((app, index) => (
                    <div
                      key={app.name}
                      className="flex items-center gap-3"
                    >
                      <span className="text-xs text-text-muted w-4">{index + 1}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-text-secondary truncate">{app.name}</span>
                          <span className="text-sm font-medium text-text-primary ml-2">
                            {app.count}
                          </span>
                        </div>
                        <div className="h-1 bg-bg-tertiary rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-violet-500 to-violet-400 rounded-full"
                            style={{ width: `${(app.count / stats.topApps[0].count) * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Eye className="w-8 h-8 text-text-muted mx-auto mb-2" />
                  <p className="text-sm text-text-muted">
                    Активность ещё не записана
                  </p>
                </div>
              )}
            </div>

            {/* Quick Actions */}
            <div className="space-y-4">
              {/* Sync Status */}
              <div className="bg-bg-secondary rounded-xl p-5 border border-border-subtle">
                <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 text-violet-400" />
                  Синхронизация
                </h2>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-text-secondary">Последняя синхронизация</span>
                  <span className="text-sm font-medium text-text-primary">{stats.lastSync}</span>
                </div>
                <button
                  onClick={() => invoke('sync_now')}
                  disabled={stats.status === 'syncing'}
                  className="w-full py-2.5 bg-bg-tertiary hover:bg-bg-hover text-text-secondary text-sm rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 border border-border-subtle"
                >
                  <RefreshCw
                    className={`w-4 h-4 ${stats.status === 'syncing' ? 'animate-spin' : ''}`}
                  />
                  {stats.status === 'syncing' ? 'Синхронизация...' : 'Синхронизировать сейчас'}
                </button>
              </div>

              {/* Status Card */}
              <div className="bg-bg-secondary rounded-xl p-5 border border-border-subtle">
                <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-violet-400" />
                  Статус
                </h2>
                <div className="flex items-center gap-3 p-3 bg-bg-tertiary rounded-lg">
                  <div className={`w-3 h-3 rounded-full ${
                    stats.status === 'collecting'
                      ? 'bg-status-success'
                      : stats.status === 'syncing'
                      ? 'bg-status-info animate-pulse'
                      : 'bg-status-warning'
                  }`} />
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      {stats.status === 'collecting' ? 'Активен' : stats.status === 'paused' ? 'Пауза' : 'Синхронизация'}
                    </p>
                    <p className="text-xs text-text-muted">
                      {stats.status === 'collecting' ? 'Собираю данные активности' : stats.status === 'paused' ? 'Сбор приостановлен' : 'Отправка на сервер...'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

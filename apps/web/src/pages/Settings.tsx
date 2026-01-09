import { useState, useEffect } from 'react';
import { Save, Trash2, RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
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
              const validatedSettings = serverSettings.settings as unknown as SettingsData;
              setSettings(validatedSettings);
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
        await api.saveSettings(deviceId, settings as unknown as Record<string, unknown>);
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
    <div className="space-y-8 max-w-2xl mx-auto">
      {/* Header with scan line effect */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative"
      >
        <h1 className="text-3xl font-bold text-cyan-400 tracking-wider relative">
          НАСТРОЙКИ СИСТЕМЫ
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/20 to-transparent"
            animate={{ x: ['-100%', '200%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          />
        </h1>
        <p className="text-purple-400/60 mt-2 font-mono text-sm">
          &gt; Конфигурация Observer
        </p>
      </motion.div>

      {/* General Settings - Glassmorphism Panel */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <Card className="bg-black/40 backdrop-blur-xl border-2 border-cyan-500/30 shadow-[0_0_30px_rgba(6,182,212,0.15)] hover:shadow-[0_0_40px_rgba(6,182,212,0.25)] transition-shadow">
          <CardHeader className="border-b border-cyan-500/20">
            <CardTitle className="text-cyan-300 tracking-wide flex items-center gap-2">
              <span className="w-1 h-5 bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.8)]" />
              ОБЩИЕ ПАРАМЕТРЫ
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="group">
              <Switch
                label="Включить уведомления"
                checked={settings.notifications}
                onChange={(checked) =>
                  setSettings((s) => ({ ...s, notifications: checked }))
                }
                className="[&_.switch-track]:bg-purple-900/30 [&_.switch-track.checked]:bg-cyan-500/50 [&_.switch-track.checked]:shadow-[0_0_15px_rgba(6,182,212,0.6)] [&_.switch-thumb]:bg-cyan-400 [&_.switch-thumb]:shadow-[0_0_8px_rgba(6,182,212,0.8)]"
              />
            </div>

            <div className="group">
              <Switch
                label="Запускать при загрузке системы"
                checked={settings.autoStart}
                onChange={(checked) =>
                  setSettings((s) => ({ ...s, autoStart: checked }))
                }
                className="[&_.switch-track]:bg-purple-900/30 [&_.switch-track.checked]:bg-cyan-500/50 [&_.switch-track.checked]:shadow-[0_0_15px_rgba(6,182,212,0.6)] [&_.switch-thumb]:bg-cyan-400 [&_.switch-thumb]:shadow-[0_0_8px_rgba(6,182,212,0.8)]"
              />
            </div>

            <div className="relative">
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
                className="[&_select]:border-2 [&_select]:border-purple-500/30 [&_select]:bg-black/40 [&_select]:text-cyan-100 [&_select]:focus:border-cyan-400 [&_select]:focus:shadow-[0_0_15px_rgba(6,182,212,0.4)]"
              />
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Data & Privacy - Glassmorphism Panel */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <Card className="bg-black/40 backdrop-blur-xl border-2 border-purple-500/30 shadow-[0_0_30px_rgba(168,85,247,0.15)] hover:shadow-[0_0_40px_rgba(168,85,247,0.25)] transition-shadow">
          <CardHeader className="border-b border-purple-500/20">
            <CardTitle className="text-purple-300 tracking-wide flex items-center gap-2">
              <span className="w-1 h-5 bg-purple-400 shadow-[0_0_10px_rgba(168,85,247,0.8)]" />
              ДАННЫЕ И КОНФИДЕНЦИАЛЬНОСТЬ
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="relative">
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
                className="[&_select]:border-2 [&_select]:border-purple-500/30 [&_select]:bg-black/40 [&_select]:text-cyan-100 [&_select]:focus:border-purple-400 [&_select]:focus:shadow-[0_0_15px_rgba(168,85,247,0.4)]"
              />
            </div>

            <div className="pt-4 border-t border-red-500/30 relative">
              <motion.div
                className="absolute inset-0 bg-red-500/5"
                animate={{ opacity: [0.05, 0.1, 0.05] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <h4 className="text-sm font-semibold text-red-400 mb-2 tracking-wide relative">
                ОПАСНАЯ ЗОНА
              </h4>
              <p className="text-sm text-purple-300/60 mb-4 font-mono relative">
                Очистить все локальные данные, включая настройки и кэшированную информацию.
              </p>
              <Button
                variant="danger"
                onClick={handleClearData}
                aria-label="Очистить локальные данные"
                className="relative hover:shadow-[0_0_20px_rgba(239,68,68,0.5)]"
              >
                <Trash2 className="w-4 h-4" />
                Очистить локальные данные
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Connection - Glassmorphism Panel */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <Card className="bg-black/40 backdrop-blur-xl border-2 border-cyan-500/30 shadow-[0_0_30px_rgba(6,182,212,0.15)] hover:shadow-[0_0_40px_rgba(6,182,212,0.25)] transition-shadow">
          <CardHeader className="border-b border-cyan-500/20">
            <CardTitle className="text-cyan-300 tracking-wide flex items-center gap-2">
              <span className="w-1 h-5 bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.8)]" />
              ПОДКЛЮЧЕНИЕ
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-6">
            <div className="relative">
              <Input
                label="URL сервера"
                value={config.apiUrl}
                disabled
                className="[&_input]:border-2 [&_input]:border-cyan-500/30 [&_input]:bg-black/40 [&_input]:text-cyan-100 [&_input]:font-mono"
              />
              <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <AnimatePresence mode="wait">
                    {connectionStatus === 'unknown' && (
                      <motion.div
                        key="unknown"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center gap-2"
                      >
                        <span className="w-2 h-2 bg-gray-500 rounded-full" />
                        <span className="text-sm text-gray-400 font-mono">Не проверено</span>
                      </motion.div>
                    )}
                    {connectionStatus === 'checking' && (
                      <motion.div
                        key="checking"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center gap-2"
                      >
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        >
                          <RefreshCw className="w-4 h-4 text-cyan-400" />
                        </motion.div>
                        <span className="text-sm text-cyan-400 font-mono">Проверка...</span>
                      </motion.div>
                    )}
                    {connectionStatus === 'healthy' && (
                      <motion.div
                        key="healthy"
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center gap-2"
                      >
                        <motion.div
                          animate={{ opacity: [1, 0.5, 1] }}
                          transition={{ duration: 2, repeat: Infinity }}
                        >
                          <CheckCircle className="w-4 h-4 text-green-400 drop-shadow-[0_0_8px_rgba(34,197,94,0.8)]" />
                        </motion.div>
                        <span className="text-sm text-green-400 font-mono">Подключено</span>
                      </motion.div>
                    )}
                    {connectionStatus === 'degraded' && (
                      <motion.div
                        key="degraded"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center gap-2"
                      >
                        <motion.div
                          animate={{ opacity: [1, 0.5, 1] }}
                          transition={{ duration: 1.5, repeat: Infinity }}
                        >
                          <AlertCircle className="w-4 h-4 text-yellow-400 drop-shadow-[0_0_8px_rgba(234,179,8,0.8)]" />
                        </motion.div>
                        <span className="text-sm text-yellow-400 font-mono">Ограниченная работа</span>
                      </motion.div>
                    )}
                    {connectionStatus === 'unhealthy' && (
                      <motion.div
                        key="unhealthy"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center gap-2"
                      >
                        <motion.div
                          animate={{ opacity: [1, 0.3, 1] }}
                          transition={{ duration: 1, repeat: Infinity }}
                        >
                          <XCircle className="w-4 h-4 text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.8)]" />
                        </motion.div>
                        <span className="text-sm text-red-400 font-mono">Отключено</span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCheckConnection}
                  disabled={connectionStatus === 'checking'}
                  aria-label="Проверить подключение к серверу"
                  className="border border-cyan-500/30 hover:border-cyan-400 hover:shadow-[0_0_15px_rgba(6,182,212,0.3)]"
                >
                  <RefreshCw className={`w-4 h-4 ${connectionStatus === 'checking' ? 'animate-spin' : ''}`} />
                  Проверить подключение
                </Button>
              </div>
              {connectionDetails && (
                <motion.p
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-xs text-purple-300/70 font-mono"
                >
                  {connectionDetails}
                </motion.p>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Save Button with Pulse Effect */}
      <motion.div
        className="flex justify-end"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Button
            onClick={handleSave}
            disabled={isLoading || isSaving}
            aria-label="Сохранить настройки"
            className="relative bg-gradient-to-r from-cyan-600 to-purple-600 border-2 border-cyan-400/50 shadow-[0_0_20px_rgba(6,182,212,0.4)] hover:shadow-[0_0_30px_rgba(6,182,212,0.6)] disabled:opacity-50"
          >
            <AnimatePresence>
              {isSaving && (
                <motion.div
                  className="absolute inset-0 bg-cyan-400/20 rounded"
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              )}
            </AnimatePresence>
            <Save className="w-4 h-4" />
            {isSaving ? 'Сохранение...' : 'Сохранить настройки'}
          </Button>
        </motion.div>
      </motion.div>
    </div>
  );
}

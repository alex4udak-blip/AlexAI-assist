import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Check, X, RefreshCw, ExternalLink } from 'lucide-react';

interface AppPermission {
  app_name: string;
  bundle_id: string;
  granted: boolean;
}

export function PermissionsPanel() {
  const [permissions, setPermissions] = useState<AppPermission[]>([]);
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);

  const loadPermissions = async () => {
    try {
      const perms = await invoke<AppPermission[]>('get_automation_permissions');
      setPermissions(perms);
    } catch (e) {
      console.error('Failed to load permissions:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPermissions();
  }, []);

  const requestAll = async () => {
    setRequesting(true);
    try {
      const results = await invoke<AppPermission[]>('request_all_automations');
      setPermissions(results);
    } catch (e) {
      console.error('Failed to request permissions:', e);
    } finally {
      setRequesting(false);
    }
  };

  const requestSingle = async (appName: string) => {
    try {
      await invoke('request_app_automation', { appName });
      await loadPermissions();
    } catch (e) {
      console.error('Failed to request permission:', e);
    }
  };

  const openSettings = async () => {
    try {
      await invoke('open_automation_prefs');
    } catch (e) {
      console.error('Failed to open settings:', e);
    }
  };

  const granted = permissions.filter((p) => p.granted).length;
  const total = permissions.length;

  if (loading) {
    return (
      <div className="p-4 text-gray-400 flex items-center gap-2">
        <RefreshCw className="w-4 h-4 animate-spin" />
        Loading permissions...
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-white">
          App Permissions ({granted}/{total})
        </h3>
        <button
          onClick={openSettings}
          className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
        >
          System Settings
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>

      <p className="text-xs text-gray-500">
        Observer needs Automation permission to read browser URLs and app data.
      </p>

      <div className="space-y-1 max-h-48 overflow-y-auto">
        {permissions.map((p) => (
          <div
            key={p.bundle_id}
            className="flex items-center justify-between py-1.5 px-2 bg-gray-800/50 rounded"
          >
            <div className="flex items-center gap-2">
              {p.granted ? (
                <Check className="w-3.5 h-3.5 text-green-400" />
              ) : (
                <X className="w-3.5 h-3.5 text-red-400" />
              )}
              <span className="text-sm text-white">{p.app_name}</span>
            </div>
            {!p.granted && (
              <button
                onClick={() => requestSingle(p.app_name)}
                className="text-xs px-2 py-0.5 bg-blue-600 hover:bg-blue-500 rounded text-white"
              >
                Request
              </button>
            )}
          </div>
        ))}
      </div>

      <button
        onClick={requestAll}
        disabled={requesting || granted === total}
        className={`w-full py-2 rounded text-sm font-medium ${
          requesting || granted === total
            ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-500 text-white'
        }`}
      >
        {requesting
          ? 'Requesting...'
          : granted === total
            ? 'All Permissions Granted'
            : 'Request All Permissions'}
      </button>

      <button
        onClick={loadPermissions}
        className="w-full py-1.5 rounded text-xs text-gray-400 hover:text-white hover:bg-gray-800 flex items-center justify-center gap-1"
      >
        <RefreshCw className="w-3 h-3" />
        Refresh Status
      </button>
    </div>
  );
}

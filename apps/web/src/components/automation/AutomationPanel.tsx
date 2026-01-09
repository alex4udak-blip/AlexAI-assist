import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { DeviceCard, type DeviceStatus } from './DeviceCard';
import { CommandHistory, type CommandRecord } from './CommandHistory';
import { AIUsageCard, type AIUsage } from './AIUsageCard';
import { apiFetch } from '../../lib/config';
import { useDeviceUpdates, useCommandResults } from '../../hooks/useWebSocketSync';
import { useWebSocket } from '../../hooks/useWebSocket';
import {
  Camera,
  ScanText,
  Globe,
  Navigation,
  Type,
  MousePointer,
  CheckCircle2,
  XCircle,
  Loader2,
  Image as ImageIcon,
  Copy,
  Check,
  X,
} from 'lucide-react';

interface CommandResult {
  command_id: string;
  status: 'pending' | 'completed' | 'failed';
  success?: boolean;
  duration_ms?: number;
  error_message?: string;
  data?: Record<string, unknown>;
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export function AutomationPanel() {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [commandHistory, setCommandHistory] = useState<CommandRecord[]>([]);
  const [aiUsage, setAiUsage] = useState<AIUsage | null>(null);
  const [aiUsageLoading, setAiUsageLoading] = useState(true);

  // Command result display
  const [lastResult, setLastResult] = useState<{
    success: boolean;
    duration?: number;
    error?: string;
    data?: Record<string, unknown>;
  } | null>(null);

  // Copy state for OCR results
  const [copied, setCopied] = useState(false);

  // Screenshot history
  const [screenshots, setScreenshots] = useState<
    Array<{
      screenshot: string;
      timestamp: string;
      command_id: string;
    }>
  >([]);
  const [selectedScreenshot, setSelectedScreenshot] = useState<string | null>(
    null
  );

  // Input states
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [coordX, setCoordX] = useState('');
  const [coordY, setCoordY] = useState('');

  // Connect to WebSocket
  const { isConnected } = useWebSocket();

  const fetchDevices = useCallback(async () => {
    try {
      const response = await apiFetch('/api/v1/automation/devices');
      if (response.ok) {
        const data = await response.json();

        // Fetch sync status for each device
        const devicesWithSync = await Promise.all(
          data.map(async (device: DeviceStatus) => {
            try {
              const syncResponse = await apiFetch(
                `/api/v1/automation/devices/${device.device_id}/sync-status`
              );
              if (syncResponse.ok) {
                const syncData = await syncResponse.json();
                return { ...device, sync_status: syncData };
              }
            } catch (error) {
              console.error(`Failed to fetch sync status for ${device.device_id}:`, error);
            }
            return device;
          })
        );

        setDevices(devicesWithSync);
        if (!selectedDevice && devicesWithSync.length > 0) {
          setSelectedDevice(devicesWithSync[0].device_id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    }
  }, [selectedDevice]);

  const fetchAIUsage = useCallback(async () => {
    try {
      const response = await apiFetch('/api/v1/analytics/ai-usage');
      if (response.ok) {
        const data = await response.json();
        // Transform backend format to frontend format
        const budgetStatus = data.budget_status || {};
        const modelBreakdown = data.model_breakdown || {};

        const haikuLimit = budgetStatus.haiku?.limit || 2;
        const sonnetLimit = budgetStatus.sonnet?.limit || 3;
        const opusLimit = budgetStatus.opus?.limit || 5;

        const haikuUsed = budgetStatus.haiku?.used || 0;
        const sonnetUsed = budgetStatus.sonnet?.used || 0;
        const opusUsed = budgetStatus.opus?.used || 0;

        const transformed: AIUsage = {
          daily_usage: {
            haiku: {
              requests: modelBreakdown.haiku?.requests || 0,
              cost: haikuUsed,
            },
            sonnet: {
              requests: modelBreakdown.sonnet?.requests || 0,
              cost: sonnetUsed,
            },
            opus: {
              requests: modelBreakdown.opus?.requests || 0,
              cost: opusUsed,
            },
          },
          daily_budget: haikuLimit + sonnetLimit + opusLimit,
          total_spent_today: haikuUsed + sonnetUsed + opusUsed,
        };
        setAiUsage(transformed);
      }
    } catch (error) {
      console.error('Failed to fetch AI usage:', error);
    } finally {
      setAiUsageLoading(false);
    }
  }, []);

  // Fetch devices on mount and when WebSocket connects
  useEffect(() => {
    fetchDevices();
    fetchAIUsage();
  }, [isConnected, fetchDevices, fetchAIUsage]);

  // Handle real-time device updates via WebSocket
  const handleDeviceUpdate = useCallback((update: { device_id: string; status: Record<string, unknown> }) => {
    setDevices((prev) => {
      const existing = prev.find((d) => d.device_id === update.device_id);
      if (existing) {
        return prev.map((d) =>
          d.device_id === update.device_id
            ? {
                ...d,
                connected: (update.status.connected as boolean) ?? d.connected,
                active_app: (update.status.active_app as string | null) ?? d.active_app,
                queue_size: (update.status.queue_size as number) ?? d.queue_size,
                last_seen: (update.status.last_seen_at as string) ?? d.last_seen,
              }
            : d
        );
      }
      // New device connected - create with required defaults
      const newDevice: DeviceStatus = {
        device_id: update.device_id,
        connected: (update.status.connected as boolean) ?? true,
        active_app: (update.status.active_app as string | null) ?? null,
        queue_size: (update.status.queue_size as number) ?? 0,
        permissions: {
          accessibility: (update.status.accessibility as boolean) ?? false,
          screen_recording: (update.status.screen_recording as boolean) ?? false,
        },
        last_seen: update.status.last_seen_at as string,
      };
      return [...prev, newDevice];
    });
  }, []);

  // Handle real-time command results via WebSocket
  const handleCommandResult = useCallback((result: { command_id: string; device_id: string; result: Record<string, unknown> }) => {
    const { command_id, result: resultData } = result;

    // Update command history
    setCommandHistory((prev) => {
      const existing = prev.find((c) => c.command_id === command_id);
      if (existing) {
        return prev;
      }

      const newRecord: CommandRecord = {
        command_id,
        command_type: 'unknown',
        timestamp: new Date().toISOString(),
        success: Boolean(resultData.success),
        duration_ms: Number(resultData.duration_ms) || 0,
        error_message: resultData.error ? String(resultData.error) : undefined,
        result: resultData.result as Record<string, unknown> | undefined,
      };

      return [newRecord, ...prev.slice(0, 19)];
    });

    // Update last result display
    setLastResult({
      success: Boolean(resultData.success),
      duration: resultData.duration_ms ? Number(resultData.duration_ms) : undefined,
      error: resultData.error ? String(resultData.error) : undefined,
      data: resultData.result as Record<string, unknown> | undefined,
    });

    setLoading(false);
  }, []);

  // Subscribe to WebSocket updates
  useDeviceUpdates(handleDeviceUpdate);
  useCommandResults(handleCommandResult);

  const fetchScreenshots = async (deviceId: string) => {
    try {
      const response = await apiFetch(
        `/api/v1/automation/devices/${deviceId}/screenshots`
      );
      if (response.ok) {
        const data = await response.json();
        setScreenshots(data);
      }
    } catch (error) {
      console.error('Failed to fetch screenshots:', error);
    }
  };

  // Fetch screenshots when selected device changes
  useEffect(() => {
    if (selectedDevice) {
      fetchScreenshots(selectedDevice);
    } else {
      setScreenshots([]);
    }
  }, [selectedDevice]);

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy text:', error);
    }
  };

  const executeCommand = async (
    commandType: string,
    params: Record<string, unknown> = {}
  ) => {
    if (!selectedDevice) {
      alert('Please select a device first');
      return;
    }

    setLoading(true);
    setLastResult(null);
    setCopied(false);

    try {
      const response = await apiFetch(
        `/api/v1/automation/command/${selectedDevice}`,
        {
          method: 'POST',
          body: JSON.stringify({
            command_type: commandType,
            params,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result: CommandResult = await response.json();

      // Command sent successfully - result will arrive via WebSocket
      // Store the command in history with pending status
      const newRecord: CommandRecord = {
        command_id: result.command_id,
        command_type: commandType,
        timestamp: new Date().toISOString(),
        success: false,
        duration_ms: 0,
      };
      setCommandHistory((prev) => [newRecord, ...prev.slice(0, 19)]);

      // Set a timeout in case WebSocket result doesn't arrive
      const timeout = setTimeout(() => {
        setLastResult({
          success: false,
          error: 'Command timeout - result not received via WebSocket',
        });
        setLoading(false);
      }, 30000);

      // Cleanup will happen when WebSocket result arrives (in handleCommandResult)
      return () => clearTimeout(timeout);
    } catch (error) {
      console.error('Command execution failed:', error);
      setLastResult({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      setLoading(false);
    }
  };

  const selectedDeviceData = devices.find((d) => d.device_id === selectedDevice);

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Device Selection */}
      <motion.div variants={item}>
        <h2 className="text-lg font-semibold text-text-primary mb-3">
          Connected Devices
        </h2>
        {devices.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-text-tertiary">
              <p>No devices connected</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {devices.map((device) => (
              <DeviceCard
                key={device.device_id}
                device={device}
                selected={device.device_id === selectedDevice}
                onClick={() => setSelectedDevice(device.device_id)}
              />
            ))}
          </div>
        )}
      </motion.div>

      {/* Quick Actions */}
      {selectedDeviceData && (
        <motion.div variants={item}>
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Simple actions grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <Button
                  variant="secondary"
                  onClick={() => executeCommand('screenshot')}
                  disabled={loading}
                  className="w-full"
                >
                  <Camera className="w-4 h-4" />
                  Screenshot
                </Button>

                <Button
                  variant="secondary"
                  onClick={() => executeCommand('ocr')}
                  disabled={loading}
                  className="w-full"
                >
                  <ScanText className="w-4 h-4" />
                  OCR
                </Button>

                <Button
                  variant="secondary"
                  onClick={() => executeCommand('get_url')}
                  disabled={loading}
                  className="w-full"
                >
                  <Globe className="w-4 h-4" />
                  Get URL
                </Button>
              </div>

              {/* Navigate to URL */}
              <div className="flex gap-2">
                <Input
                  placeholder="Enter URL..."
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  className="flex-1"
                />
                <Button
                  variant="secondary"
                  onClick={() => {
                    if (urlInput.trim()) {
                      executeCommand('navigate', { url: urlInput });
                      setUrlInput('');
                    }
                  }}
                  disabled={loading || !urlInput.trim()}
                >
                  <Navigation className="w-4 h-4" />
                  Navigate
                </Button>
              </div>

              {/* Type text */}
              <div className="flex gap-2">
                <Input
                  placeholder="Text to type..."
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  className="flex-1"
                />
                <Button
                  variant="secondary"
                  onClick={() => {
                    if (textInput.trim()) {
                      executeCommand('type', { text: textInput });
                      setTextInput('');
                    }
                  }}
                  disabled={loading || !textInput.trim()}
                >
                  <Type className="w-4 h-4" />
                  Type
                </Button>
              </div>

              {/* Click at coordinates */}
              <div className="flex gap-2">
                <Input
                  type="number"
                  placeholder="X"
                  value={coordX}
                  onChange={(e) => setCoordX(e.target.value)}
                  className="flex-1"
                />
                <Input
                  type="number"
                  placeholder="Y"
                  value={coordY}
                  onChange={(e) => setCoordY(e.target.value)}
                  className="flex-1"
                />
                <Button
                  variant="secondary"
                  onClick={() => {
                    if (coordX && coordY) {
                      executeCommand('click', {
                        x: parseInt(coordX),
                        y: parseInt(coordY),
                      });
                      setCoordX('');
                      setCoordY('');
                    }
                  }}
                  disabled={loading || !coordX || !coordY}
                >
                  <MousePointer className="w-4 h-4" />
                  Click
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Result Display */}
      {(loading || lastResult) && (
        <motion.div variants={item}>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 text-accent-primary animate-spin" />
                    <CardTitle>Executing Command...</CardTitle>
                  </>
                ) : lastResult?.success ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-status-success" />
                    <CardTitle>Command Successful</CardTitle>
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4 text-status-error" />
                    <CardTitle>Command Failed</CardTitle>
                  </>
                )}
              </div>
            </CardHeader>

            <CardContent className="space-y-3">
              {lastResult && (
                <>
                  {lastResult.duration !== undefined && (
                    <div>
                      <span className="text-xs text-text-tertiary">Duration</span>
                      <p className="text-sm text-text-secondary">
                        {(lastResult.duration / 1000).toFixed(2)}s
                      </p>
                    </div>
                  )}

                  {lastResult.error && (
                    <div>
                      <span className="text-xs text-text-tertiary">Error</span>
                      <p className="text-sm text-status-error font-mono">
                        {lastResult.error}
                      </p>
                    </div>
                  )}

                  {lastResult.data ? (
                    <div className="space-y-3">
                      {/* OCR Results Section */}
                      {(typeof lastResult.data.text === 'string' || typeof lastResult.data.ocr_text === 'string') ? (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <ScanText className="w-4 h-4 text-accent-primary" />
                              <span className="text-sm font-medium text-text-primary">
                                OCR Text
                              </span>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                copyToClipboard(
                                  String(lastResult.data?.text || lastResult.data?.ocr_text || '')
                                )
                              }
                              className="h-7 px-2"
                            >
                              {copied ? (
                                <>
                                  <Check className="w-3 h-3" />
                                  Copied
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3 h-3" />
                                  Copy
                                </>
                              )}
                            </Button>
                          </div>
                          <div className="bg-bg-tertiary rounded-lg p-3 border border-border-default">
                            <p className="text-sm text-text-secondary whitespace-pre-wrap font-mono">
                              {String(lastResult.data.text || lastResult.data.ocr_text)}
                            </p>
                            {lastResult.data.confidence != null && (
                              <div className="mt-2 pt-2 border-t border-border-default">
                                <span className="text-xs text-text-tertiary">
                                  Confidence:{' '}
                                  {typeof lastResult.data.confidence === 'number'
                                    ? `${(lastResult.data.confidence * 100).toFixed(1)}%`
                                    : String(lastResult.data.confidence)}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      ) : null}

                      {/* Screenshot Section */}
                      {typeof lastResult.data.screenshot === 'string' ? (
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <ImageIcon className="w-4 h-4 text-accent-primary" />
                            <span className="text-sm font-medium text-text-primary">
                              Screenshot
                            </span>
                          </div>
                          <img
                            src={`data:image/png;base64,${lastResult.data.screenshot}`}
                            alt="Screenshot"
                            className="rounded-lg border border-border-default max-w-full h-auto"
                          />
                        </div>
                      ) : null}

                      {/* Other Result Data */}
                      {Object.keys(lastResult.data).some(
                        (key) =>
                          !['text', 'ocr_text', 'screenshot', 'confidence'].includes(
                            key
                          )
                      ) ? (
                        <div>
                          <span className="text-xs text-text-tertiary block mb-1">
                            Additional Data
                          </span>
                          <pre className="text-xs text-text-secondary bg-bg-tertiary rounded p-3 overflow-x-auto">
                            {JSON.stringify(
                              Object.fromEntries(
                                Object.entries(lastResult.data).filter(
                                  ([key]) =>
                                    !['text', 'ocr_text', 'screenshot', 'confidence'].includes(
                                      key
                                    )
                                )
                              ),
                              null,
                              2
                            )}
                          </pre>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* AI Usage and Command History */}
      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AIUsageCard usage={aiUsage} loading={aiUsageLoading} />
        <CommandHistory commands={commandHistory} />
      </motion.div>

      {/* Screenshot History */}
      {selectedDevice && screenshots.length > 0 && (
        <motion.div variants={item}>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-accent-primary" />
                <CardTitle>Screenshot History</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {screenshots.map((screenshot, index) => {
                  const timestamp = new Date(screenshot.timestamp);
                  const timeAgo = Math.floor(
                    (Date.now() - timestamp.getTime()) / 1000
                  );
                  const timeLabel =
                    timeAgo < 60
                      ? `${timeAgo}s ago`
                      : timeAgo < 3600
                        ? `${Math.floor(timeAgo / 60)}m ago`
                        : `${Math.floor(timeAgo / 3600)}h ago`;

                  return (
                    <div
                      key={screenshot.command_id}
                      className="group relative cursor-pointer rounded-lg overflow-hidden border border-border-default hover:border-accent-primary transition-colors"
                      onClick={() => setSelectedScreenshot(screenshot.screenshot)}
                    >
                      <img
                        src={`data:image/png;base64,${screenshot.screenshot}`}
                        alt={`Screenshot ${index + 1}`}
                        className="w-full h-32 object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                        <div className="absolute bottom-0 left-0 right-0 p-2">
                          <p className="text-xs text-white font-medium">
                            {timeLabel}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Screenshot Modal */}
      {selectedScreenshot && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setSelectedScreenshot(null)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="relative max-w-6xl max-h-[90vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedScreenshot(null)}
              className="absolute top-4 right-4 p-2 rounded-full bg-bg-primary/90 hover:bg-bg-secondary border border-border-default transition-colors z-10"
            >
              <X className="w-5 h-5 text-text-primary" />
            </button>
            <img
              src={`data:image/png;base64,${selectedScreenshot}`}
              alt="Screenshot"
              className="rounded-lg border border-border-default max-w-full h-auto"
            />
          </motion.div>
        </div>
      )}
    </motion.div>
  );
}

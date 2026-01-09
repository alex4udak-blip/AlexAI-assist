import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { DeviceCard, type DeviceStatus } from './DeviceCard';
import { CommandHistory, type CommandRecord } from './CommandHistory';
import { AIUsageCard, type AIUsage } from './AIUsageCard';
import { config } from '../../lib/config';
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
} from 'lucide-react';

const API_URL = config.apiUrl;

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

  // Input states
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [coordX, setCoordX] = useState('');
  const [coordY, setCoordY] = useState('');

  // Fetch devices
  useEffect(() => {
    fetchDevices();
    fetchAIUsage();
    const interval = setInterval(() => {
      fetchDevices();
      fetchAIUsage();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDevices = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/automation/devices`);
      if (response.ok) {
        const data = await response.json();
        setDevices(data);
        if (!selectedDevice && data.length > 0) {
          setSelectedDevice(data[0].device_id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    }
  };

  const fetchAIUsage = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/analytics/ai-usage`);
      if (response.ok) {
        const data = await response.json();
        setAiUsage(data);
      }
    } catch (error) {
      console.error('Failed to fetch AI usage:', error);
    } finally {
      setAiUsageLoading(false);
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

    try {
      const response = await fetch(
        `${API_URL}/api/v1/automation/command/${selectedDevice}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
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

      // Poll for result
      const commandId = result.command_id;
      let attempts = 0;
      const maxAttempts = 30;

      const pollResult = async () => {
        attempts++;
        const resultResponse = await fetch(
          `${API_URL}/api/v1/automation/result/${commandId}`
        );

        if (resultResponse.ok) {
          const resultData: CommandResult = await resultResponse.json();

          if (resultData.status === 'completed' || resultData.status === 'failed') {
            const newRecord: CommandRecord = {
              command_id: commandId,
              command_type: commandType,
              timestamp: new Date().toISOString(),
              success: resultData.success ?? false,
              duration_ms: resultData.duration_ms ?? 0,
              error_message: resultData.error_message,
              result: resultData.data,
            };

            setCommandHistory((prev) => [newRecord, ...prev.slice(0, 19)]);
            setLastResult({
              success: resultData.success ?? false,
              duration: resultData.duration_ms,
              error: resultData.error_message,
              data: resultData.data,
            });
            setLoading(false);
            return;
          }
        }

        if (attempts < maxAttempts) {
          setTimeout(pollResult, 1000);
        } else {
          setLastResult({
            success: false,
            error: 'Command timeout - result not received',
          });
          setLoading(false);
        }
      };

      await pollResult();
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

                  {lastResult.data && (
                    <div>
                      <span className="text-xs text-text-tertiary block mb-1">
                        Result Data
                      </span>
                      {lastResult.data.screenshot && (
                        <div className="mb-3">
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
                      )}
                      <pre className="text-xs text-text-secondary bg-bg-tertiary rounded p-3 overflow-x-auto">
                        {JSON.stringify(lastResult.data, null, 2)}
                      </pre>
                    </div>
                  )}
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
    </motion.div>
  );
}

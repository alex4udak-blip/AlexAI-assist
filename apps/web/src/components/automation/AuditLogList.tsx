import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { api, type AuditLog } from '../../lib/api';
import {
  Clock,
  Monitor,
  AlertCircle,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

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

export function AuditLogList() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterDevice, setFilterDevice] = useState<string>('');
  const [filterActionType, setFilterActionType] = useState<string>('');
  const [filterResult, setFilterResult] = useState<string>('');
  const [expandedLog, setExpandedLog] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      const params: Record<string, string | number> = { limit: 50 };
      if (filterDevice) params.device_id = filterDevice;
      if (filterActionType) params.action_type = filterActionType;
      if (filterResult) params.result = filterResult;

      const data = await api.getAuditLogs(params);
      setLogs(data);
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    } finally {
      setLoading(false);
    }
  }, [filterDevice, filterActionType, filterResult]);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 10000);
    return () => clearInterval(interval);
  }, [fetchLogs]);

  const getResultBadge = (result: string) => {
    switch (result) {
      case 'success':
        return <Badge variant="success">Успешно</Badge>;
      case 'failure':
        return <Badge variant="error">Ошибка</Badge>;
      case 'pending':
        return <Badge variant="warning">Ожидание</Badge>;
      case 'timeout':
        return <Badge variant="warning">Таймаут</Badge>;
      default:
        return <Badge variant="default">{result}</Badge>;
    }
  };

  const getResultIcon = (result: string) => {
    switch (result) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-status-success" />;
      case 'failure':
        return <XCircle className="w-4 h-4 text-status-error" />;
      case 'pending':
        return <Loader2 className="w-4 h-4 text-status-warning animate-spin" />;
      case 'timeout':
        return <AlertCircle className="w-4 h-4 text-status-warning" />;
      default:
        return <AlertCircle className="w-4 h-4 text-text-tertiary" />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const formatDuration = (durationMs: number | null) => {
    if (durationMs === null) return 'N/A';
    if (durationMs < 1000) return `${durationMs}ms`;
    return `${(durationMs / 1000).toFixed(2)}s`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Журнал аудита</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Input
              placeholder="Фильтр по ID устройства"
              value={filterDevice}
              onChange={(e) => setFilterDevice(e.target.value)}
            />
            <Select
              value={filterActionType}
              onChange={(e) => setFilterActionType(e.target.value)}
            >
              <option value="">Все действия</option>
              <option value="command_executed">Команда выполнена</option>
              <option value="agent_run">Запуск агента</option>
              <option value="setting_changed">Настройка изменена</option>
            </Select>
            <Select
              value={filterResult}
              onChange={(e) => setFilterResult(e.target.value)}
            >
              <option value="">Все результаты</option>
              <option value="success">Успешно</option>
              <option value="failure">Ошибка</option>
              <option value="pending">Ожидание</option>
              <option value="timeout">Таймаут</option>
            </Select>
          </div>

          {/* Logs List */}
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-accent-primary animate-spin" />
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-8 text-text-tertiary">
              Записи аудита не найдены
            </div>
          ) : (
            <motion.div
              variants={container}
              initial="hidden"
              animate="show"
              className="space-y-2"
            >
              {logs.map((log) => (
                <motion.div
                  key={log.id}
                  variants={item}
                  className="border border-border-default rounded-lg p-4 bg-bg-secondary hover:bg-bg-tertiary transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <div className="mt-1">{getResultIcon(log.result)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className="font-medium text-text-primary">
                            {log.command_type || log.action_type}
                          </span>
                          {getResultBadge(log.result)}
                          <Badge variant="info">{log.actor}</Badge>
                        </div>

                        <div className="flex items-center gap-4 text-sm text-text-tertiary flex-wrap">
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatTimestamp(log.timestamp)}
                          </div>
                          {log.device_id && (
                            <div className="flex items-center gap-1">
                              <Monitor className="w-3 h-3" />
                              {log.device_id.slice(0, 8)}
                            </div>
                          )}
                          {log.duration_ms !== null && (
                            <div className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {formatDuration(log.duration_ms)}
                            </div>
                          )}
                        </div>

                        {log.error_message && (
                          <div className="mt-2 text-sm text-status-error">
                            {log.error_message}
                          </div>
                        )}

                        {/* Expandable details */}
                        {(log.command_params || log.ip_address) && (
                          <>
                            <button
                              onClick={() =>
                                setExpandedLog(
                                  expandedLog === log.id ? null : log.id
                                )
                              }
                              className="mt-2 text-sm text-accent-primary hover:text-accent-hover flex items-center gap-1"
                            >
                              {expandedLog === log.id ? (
                                <>
                                  <ChevronUp className="w-4 h-4" />
                                  Скрыть детали
                                </>
                              ) : (
                                <>
                                  <ChevronDown className="w-4 h-4" />
                                  Показать детали
                                </>
                              )}
                            </button>

                            {expandedLog === log.id && (
                              <div className="mt-3 space-y-2 text-sm">
                                {log.command_params && (
                                  <div>
                                    <span className="text-text-tertiary block mb-1">
                                      Параметры:
                                    </span>
                                    <pre className="text-xs text-text-secondary bg-bg-tertiary rounded p-2 overflow-x-auto">
                                      {JSON.stringify(log.command_params, null, 2)}
                                    </pre>
                                  </div>
                                )}
                                {log.ip_address && (
                                  <div>
                                    <span className="text-text-tertiary">
                                      IP адрес:
                                    </span>{' '}
                                    <span className="text-text-secondary font-mono">
                                      {log.ip_address}
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

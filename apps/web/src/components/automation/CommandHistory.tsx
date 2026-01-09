import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { formatDateTime, formatDuration } from '../../lib/utils';
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';

export interface CommandRecord {
  command_id: string;
  command_type: string;
  timestamp: string;
  success: boolean;
  duration_ms: number;
  error_message?: string;
  result?: Record<string, unknown>;
}

interface CommandHistoryProps {
  commands: CommandRecord[];
}

function CommandItem({ command }: { command: CommandRecord }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-border-subtle rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-center gap-3 hover:bg-white/[0.02] transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-text-tertiary flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-text-tertiary flex-shrink-0" />
        )}

        {command.success ? (
          <CheckCircle2 className="w-4 h-4 text-status-success flex-shrink-0" />
        ) : (
          <XCircle className="w-4 h-4 text-status-error flex-shrink-0" />
        )}

        <div className="flex-1 min-w-0 text-left">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-text-primary">
              {command.command_type}
            </span>
            <Badge variant={command.success ? 'success' : 'error'}>
              {command.success ? 'Success' : 'Failed'}
            </Badge>
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-text-tertiary">
            <span>{formatDateTime(command.timestamp)}</span>
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>{formatDuration(command.duration_ms / 1000)}</span>
            </div>
          </div>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-border-subtle bg-white/[0.02]"
          >
            <div className="p-3 space-y-2">
              {command.error_message && (
                <div>
                  <span className="text-xs text-text-tertiary block mb-1">
                    Error
                  </span>
                  <p className="text-sm text-status-error font-mono">
                    {command.error_message}
                  </p>
                </div>
              )}

              {command.result && (
                <div>
                  <span className="text-xs text-text-tertiary block mb-1">
                    Result
                  </span>
                  <pre className="text-xs text-text-secondary bg-bg-tertiary rounded p-2 overflow-x-auto">
                    {JSON.stringify(command.result, null, 2)}
                  </pre>
                </div>
              )}

              <div>
                <span className="text-xs text-text-tertiary block mb-1">
                  Command ID
                </span>
                <p className="text-xs text-text-secondary font-mono">
                  {command.command_id}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function CommandHistory({ commands }: CommandHistoryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Commands</CardTitle>
      </CardHeader>

      <CardContent>
        {commands.length === 0 ? (
          <div className="text-center py-8 text-text-tertiary">
            <p className="text-sm">No commands executed yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {commands.map((command) => (
              <CommandItem key={command.command_id} command={command} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

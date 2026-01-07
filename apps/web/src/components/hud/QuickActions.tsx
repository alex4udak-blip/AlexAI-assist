import { motion } from 'framer-motion';
import { Plus, Pause, Play, FileText, Bot, Settings, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface QuickAction {
  id: string;
  label: string;
  icon: typeof Plus;
  variant: 'primary' | 'secondary' | 'warning';
  action: () => void;
}

interface QuickActionsProps {
  isTracking?: boolean;
  onToggleTracking?: () => void;
  onCreateAgent?: () => void;
}

export function QuickActions({
  isTracking = true,
  onToggleTracking,
  onCreateAgent,
}: QuickActionsProps) {
  const navigate = useNavigate();

  const actions: QuickAction[] = [
    {
      id: 'create-agent',
      label: 'Создать агента',
      icon: Plus,
      variant: 'primary',
      action: () => onCreateAgent?.() || navigate('/agents'),
    },
    {
      id: 'toggle-tracking',
      label: isTracking ? 'Пауза трекинга' : 'Возобновить',
      icon: isTracking ? Pause : Play,
      variant: isTracking ? 'warning' : 'secondary',
      action: () => onToggleTracking?.(),
    },
    {
      id: 'report',
      label: 'Детальный отчёт',
      icon: FileText,
      variant: 'secondary',
      action: () => navigate('/analytics'),
    },
  ];

  const variantStyles = {
    primary: 'bg-hud-gradient border-hud-cyan/30 text-text-primary hover:shadow-hud',
    secondary: 'bg-bg-tertiary border-border-subtle text-text-secondary hover:text-text-primary hover:border-border-default',
    warning: 'bg-status-warning/10 border-status-warning/30 text-status-warning hover:bg-status-warning/20',
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-5 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow"
    >
      <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono mb-4">
        Quick Actions
      </h3>

      <div className="space-y-2">
        {actions.map((action, index) => {
          const Icon = action.icon;
          return (
            <motion.button
              key={action.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={action.action}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg border
                         transition-all duration-200 ${variantStyles[action.variant]}`}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{action.label}</span>
            </motion.button>
          );
        })}
      </div>

      {/* Secondary actions */}
      <div className="flex gap-2 mt-4 pt-4 border-t border-border-subtle">
        <button
          onClick={() => navigate('/agents')}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg
                     text-xs text-text-muted hover:text-text-primary hover:bg-bg-tertiary
                     transition-colors"
        >
          <Bot className="w-4 h-4" />
          Все агенты
        </button>
        <button
          onClick={() => navigate('/settings')}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg
                     text-xs text-text-muted hover:text-text-primary hover:bg-bg-tertiary
                     transition-colors"
        >
          <Settings className="w-4 h-4" />
          Настройки
        </button>
      </div>
    </motion.div>
  );
}

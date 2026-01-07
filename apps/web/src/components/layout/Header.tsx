import { useLocation } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';

interface HeaderProps {
  onMenuClick?: () => void;
}

const pageTitles: Record<string, string> = {
  '/': 'Главная',
  '/agents': 'Агенты',
  '/analytics': 'Аналитика',
  '/history': 'История',
  '/chat': 'Чат',
  '/settings': 'Настройки',
  '/download': 'Скачать',
};

export default function Header({ onMenuClick }: HeaderProps) {
  const location = useLocation();
  const { isConnected } = useWebSocket();
  const title = pageTitles[location.pathname] || 'Observer';

  return (
    <header className="sticky top-0 h-14 flex items-center justify-between px-4 lg:px-6
                       border-b border-border-subtle bg-bg-primary/80 backdrop-blur-xl z-30">
      {/* Left side */}
      <div className="flex items-center gap-3">
        {/* Mobile menu button */}
        <button
          onClick={onMenuClick}
          className="p-2 -ml-2 rounded-lg text-text-tertiary hover:text-text-primary
                     hover:bg-white/[0.05] transition-colors lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Page title */}
        <h1 className="text-lg font-semibold text-text-primary tracking-tight">
          {title}
        </h1>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Connection status */}
        <div className="flex items-center gap-2 text-sm">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-status-success animate-pulse' : 'bg-text-muted'}`} />
          <span className="text-text-tertiary hidden sm:inline">
            {isConnected ? 'Подключено' : 'Отключено'}
          </span>
        </div>

      </div>
    </header>
  );
}

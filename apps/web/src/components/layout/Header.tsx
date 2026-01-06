import { useState } from 'react';
import { Search, Bell, RefreshCw } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { cn } from '../../lib/utils';

export default function Header() {
  const { isConnected } = useWebSocket();
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="h-16 border-b border-border-subtle bg-bg-secondary/50 backdrop-blur-sm sticky top-0 z-10">
      <div className="h-full px-6 flex items-center justify-between">
        <div className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-bg-tertiary border border-border-subtle rounded-lg pl-10 pr-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-primary focus:outline-none transition-colors"
            />
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <span
              className={cn(
                'w-2 h-2 rounded-full',
                isConnected ? 'bg-status-success' : 'bg-status-error'
              )}
            />
            <span className="text-text-tertiary">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          <button className="p-2 text-text-secondary hover:text-text-primary hover:bg-bg-hover rounded-lg transition-colors">
            <RefreshCw className="w-5 h-5" />
          </button>

          <button className="p-2 text-text-secondary hover:text-text-primary hover:bg-bg-hover rounded-lg transition-colors relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent-primary rounded-full" />
          </button>
        </div>
      </div>
    </header>
  );
}

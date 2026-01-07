import { motion } from 'framer-motion';
import { LayoutDashboard, Bot, MessageSquare, Settings, Plus } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

interface BottomNavigationProps {
  onCreateAgent?: () => void;
}

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/agents', icon: Bot, label: 'Agents' },
  { path: '/chat', icon: MessageSquare, label: 'Chat' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export function BottomNavigation({ onCreateAgent }: BottomNavigationProps) {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <>
      {/* FAB Button */}
      <motion.button
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        whileTap={{ scale: 0.9 }}
        onClick={onCreateAgent}
        className="fixed right-4 bottom-24 z-50 w-14 h-14 rounded-full
                   bg-hud-gradient shadow-hud flex items-center justify-center
                   active:shadow-hud-lg transition-shadow touch-manipulation
                   safe-area-bottom"
        style={{ marginBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <Plus className="w-6 h-6 text-white" />
      </motion.button>

      {/* Bottom Navigation Bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 bg-bg-primary/95 backdrop-blur-lg
                      border-t border-border-subtle safe-area-bottom">
        <div
          className="flex items-center justify-around px-2"
          style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
        >
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;

            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className="relative flex flex-col items-center justify-center py-3 px-4
                           transition-colors touch-manipulation"
                style={{ minWidth: '64px', minHeight: '64px' }}
              >
                {/* Active indicator */}
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute top-1 w-8 h-1 rounded-full bg-hud-cyan"
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                )}

                <Icon
                  className={`w-6 h-6 transition-colors
                             ${isActive ? 'text-hud-cyan' : 'text-text-muted'}`}
                />
                <span
                  className={`text-[10px] mt-1 transition-colors
                             ${isActive ? 'text-hud-cyan' : 'text-text-muted'}`}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </nav>
    </>
  );
}

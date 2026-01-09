import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home,
  Bot,
  BarChart3,
  Clock,
  MessageSquare,
  Settings,
  Download,
  X,
  Eye,
  Cpu,
} from 'lucide-react';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

const navItems = [
  { icon: Home, label: 'Главная', href: '/' },
  { icon: Bot, label: 'Агенты', href: '/agents' },
  { icon: BarChart3, label: 'Аналитика', href: '/analytics' },
  { icon: Clock, label: 'История', href: '/history' },
  { icon: MessageSquare, label: 'Чат', href: '/chat' },
  { icon: Cpu, label: 'Автоматизация', href: '/automation' },
];

const bottomItems = [
  { icon: Settings, label: 'Настройки', href: '/settings' },
  { icon: Download, label: 'Скачать', href: '/download' },
];

function NavItem({
  icon: Icon,
  label,
  href,
  onClick,
}: {
  icon: typeof Home;
  label: string;
  href: string;
  onClick?: () => void;
}) {
  const location = useLocation();
  const isActive = location.pathname === href;

  return (
    <NavLink
      to={href}
      onClick={onClick}
      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
                  transition-all duration-150 group
                  ${isActive
                    ? 'text-text-primary bg-white/[0.05]'
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.05]'
                  }`}
    >
      <Icon className={`w-4 h-4 transition-colors ${isActive ? 'text-accent-primary' : 'group-hover:text-text-primary'}`} />
      <span>{label}</span>
    </NavLink>
  );
}

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="fixed left-0 top-0 h-screen w-60 border-r border-border-subtle
                        flex flex-col bg-bg-primary z-40
                        max-lg:hidden">
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b border-border-subtle">
          <div className="w-8 h-8 rounded-lg bg-accent-gradient flex items-center justify-center shadow-glow-sm">
            <Eye className="w-4 h-4 text-white" />
          </div>
          <span className="ml-3 font-semibold text-text-primary tracking-tight">Observer</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavItem key={item.href} {...item} />
          ))}
        </nav>

        {/* Bottom */}
        <div className="p-3 border-t border-border-subtle space-y-1">
          {bottomItems.map((item) => (
            <NavItem key={item.href} {...item} />
          ))}
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 lg:hidden"
              onClick={onClose}
            />

            {/* Mobile Sidebar */}
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed left-0 top-0 h-screen w-72 border-r border-border-subtle
                         flex flex-col bg-bg-primary z-50 lg:hidden"
            >
              {/* Header */}
              <div className="h-14 flex items-center justify-between px-4 border-b border-border-subtle">
                <div className="flex items-center">
                  <div className="w-8 h-8 rounded-lg bg-accent-gradient flex items-center justify-center shadow-glow-sm">
                    <Eye className="w-4 h-4 text-white" />
                  </div>
                  <span className="ml-3 font-semibold text-text-primary tracking-tight">Observer</span>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-white/[0.05] transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Navigation */}
              <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
                {navItems.map((item) => (
                  <NavItem key={item.href} {...item} onClick={onClose} />
                ))}
              </nav>

              {/* Bottom */}
              <div className="p-3 border-t border-border-subtle space-y-1">
                {bottomItems.map((item) => (
                  <NavItem key={item.href} {...item} onClick={onClose} />
                ))}
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

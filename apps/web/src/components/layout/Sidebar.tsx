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
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';

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
      className="block relative group"
    >
      <motion.div
        whileHover={{ x: 4 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                    relative overflow-hidden transition-all duration-300
                    ${isActive
                      ? 'text-text-primary bg-surface-active'
                      : 'text-text-secondary hover:text-text-primary'
                    }`}
      >
        {/* Scan line effect on hover */}
        <motion.div
          className="absolute inset-0 bg-scanline opacity-0 group-hover:opacity-100 pointer-events-none"
          initial={{ y: '-100%' }}
          whileHover={{ y: '100%' }}
          transition={{ duration: 1.5, ease: 'linear', repeat: Infinity }}
        />

        {/* Active glow border */}
        {isActive && (
          <motion.div
            layoutId="activeNavBorder"
            className="absolute inset-0 border border-hud-cyan/50 rounded-lg shadow-glow-cyan"
            transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
          />
        )}

        {/* Icon with glow on active */}
        <div className={`relative z-10 ${isActive ? 'text-hud-cyan' : 'text-inherit group-hover:text-hud-cyan transition-colors'}`}>
          <Icon className="w-4 h-4" />
          {isActive && (
            <motion.div
              className="absolute inset-0 blur-md bg-hud-cyan/40"
              animate={{ opacity: [0.4, 0.8, 0.4] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            />
          )}
        </div>

        <span className="relative z-10">{label}</span>

        {/* Animated underline on hover */}
        <motion.div
          className="absolute bottom-0 left-3 right-3 h-[1px] bg-gradient-to-r from-transparent via-hud-cyan to-transparent"
          initial={{ opacity: 0, scaleX: 0 }}
          whileHover={{ opacity: 1, scaleX: 1 }}
          transition={{ duration: 0.3 }}
        />
      </motion.div>
    </NavLink>
  );
}

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const { isConnected } = useWebSocket();

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="fixed left-0 top-0 h-screen w-60 border-r border-border-glow
                        flex flex-col z-40 max-lg:hidden overflow-hidden
                        bg-bg-primary/95 backdrop-blur-xl">
        {/* Circuit pattern decoration */}
        <div className="absolute inset-0 bg-hud-radial opacity-30 pointer-events-none" />
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-hud-cyan to-transparent opacity-50" />
        <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-hud-cyan to-transparent opacity-50" />
        <div className="absolute left-0 top-0 w-px h-full bg-gradient-to-b from-transparent via-hud-cyan to-transparent opacity-30" />

        {/* Logo with glow */}
        <div className="h-14 flex items-center px-4 border-b border-border-glow relative z-10
                       bg-gradient-to-r from-bg-secondary/50 to-transparent">
          <motion.div
            animate={{
              boxShadow: [
                '0 0 20px rgba(6, 182, 212, 0.3)',
                '0 0 30px rgba(6, 182, 212, 0.5)',
                '0 0 20px rgba(6, 182, 212, 0.3)',
              ]
            }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="w-8 h-8 rounded-lg bg-accent-gradient flex items-center justify-center
                       border border-hud-cyan/50 relative"
          >
            <Eye className="w-4 h-4 text-white relative z-10" />
            <motion.div
              className="absolute inset-0 bg-hud-cyan/20 rounded-lg"
              animate={{ opacity: [0.2, 0.5, 0.2] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            />
          </motion.div>
          <span className="ml-3 font-semibold text-text-primary tracking-tight">
            Observer
          </span>

          {/* Connection status indicator */}
          <div className="ml-auto flex items-center gap-1.5">
            <motion.div
              animate={isConnected ? {
                scale: [1, 1.2, 1],
                opacity: [0.7, 1, 0.7],
              } : {}}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-status-success shadow-glow-green' : 'bg-status-offline'
              }`}
            />
            {isConnected ? (
              <Wifi className="w-3 h-3 text-status-success" />
            ) : (
              <WifiOff className="w-3 h-3 text-status-offline" />
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto relative z-10
                       scrollbar-thin scrollbar-track-transparent scrollbar-thumb-border-subtle">
          {navItems.map((item) => (
            <NavItem key={item.href} {...item} />
          ))}
        </nav>

        {/* Bottom section with separator glow */}
        <div className="p-3 border-t border-border-glow space-y-1 relative z-10
                       bg-gradient-to-r from-bg-secondary/30 to-transparent">
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-ring-middle to-transparent opacity-70" />
          {bottomItems.map((item) => (
            <NavItem key={item.href} {...item} />
          ))}
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop with enhanced blur */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 lg:hidden"
              onClick={onClose}
            />

            {/* Mobile Sidebar */}
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed left-0 top-0 h-screen w-72 border-r border-border-glow
                         flex flex-col z-50 lg:hidden overflow-hidden
                         bg-bg-primary/95 backdrop-blur-xl"
            >
              {/* Circuit pattern decoration */}
              <div className="absolute inset-0 bg-hud-radial opacity-30 pointer-events-none" />
              <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-hud-cyan to-transparent opacity-50" />
              <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-hud-cyan to-transparent opacity-50" />
              <div className="absolute left-0 top-0 w-px h-full bg-gradient-to-b from-transparent via-hud-cyan to-transparent opacity-30" />

              {/* Header with logo glow */}
              <div className="h-14 flex items-center justify-between px-4 border-b border-border-glow relative z-10
                             bg-gradient-to-r from-bg-secondary/50 to-transparent">
                <div className="flex items-center">
                  <motion.div
                    animate={{
                      boxShadow: [
                        '0 0 20px rgba(6, 182, 212, 0.3)',
                        '0 0 30px rgba(6, 182, 212, 0.5)',
                        '0 0 20px rgba(6, 182, 212, 0.3)',
                      ]
                    }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                    className="w-8 h-8 rounded-lg bg-accent-gradient flex items-center justify-center
                               border border-hud-cyan/50 relative"
                  >
                    <Eye className="w-4 h-4 text-white relative z-10" />
                    <motion.div
                      className="absolute inset-0 bg-hud-cyan/20 rounded-lg"
                      animate={{ opacity: [0.2, 0.5, 0.2] }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                    />
                  </motion.div>
                  <span className="ml-3 font-semibold text-text-primary tracking-tight">
                    Observer
                  </span>
                </div>

                {/* Connection status + close button */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <motion.div
                      animate={isConnected ? {
                        scale: [1, 1.2, 1],
                        opacity: [0.7, 1, 0.7],
                      } : {}}
                      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                      className={`w-2 h-2 rounded-full ${
                        isConnected ? 'bg-status-success shadow-glow-green' : 'bg-status-offline'
                      }`}
                    />
                    {isConnected ? (
                      <Wifi className="w-3 h-3 text-status-success" />
                    ) : (
                      <WifiOff className="w-3 h-3 text-status-offline" />
                    )}
                  </div>

                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={onClose}
                    className="p-2 rounded-lg text-text-tertiary hover:text-text-primary
                             hover:bg-surface-hover border border-transparent hover:border-hud-cyan/30
                             transition-all duration-300 relative overflow-hidden group"
                  >
                    <X className="w-5 h-5 relative z-10" />
                    <motion.div
                      className="absolute inset-0 bg-hud-cyan/10 opacity-0 group-hover:opacity-100"
                      transition={{ duration: 0.3 }}
                    />
                  </motion.button>
                </div>
              </div>

              {/* Navigation */}
              <nav className="flex-1 p-3 space-y-1 overflow-y-auto relative z-10
                             scrollbar-thin scrollbar-track-transparent scrollbar-thumb-border-subtle">
                {navItems.map((item) => (
                  <NavItem key={item.href} {...item} onClick={onClose} />
                ))}
              </nav>

              {/* Bottom section with separator glow */}
              <div className="p-3 border-t border-border-glow space-y-1 relative z-10
                             bg-gradient-to-r from-bg-secondary/30 to-transparent">
                <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-ring-middle to-transparent opacity-70" />
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

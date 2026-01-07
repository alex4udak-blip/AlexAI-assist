import { NavLink, useLocation } from 'react-router-dom';
import { Home, Bot, BarChart3, MessageSquare, MoreHorizontal } from 'lucide-react';

const navItems = [
  { icon: Home, label: 'Главная', href: '/' },
  { icon: Bot, label: 'Агенты', href: '/agents' },
  { icon: BarChart3, label: 'Аналитика', href: '/analytics' },
  { icon: MessageSquare, label: 'Чат', href: '/chat' },
  { icon: MoreHorizontal, label: 'Ещё', href: '/settings' },
];

export default function MobileNav() {
  const location = useLocation();

  return (
    <nav className="fixed bottom-0 left-0 right-0 h-16
                    border-t border-border-subtle bg-bg-primary/80 backdrop-blur-xl
                    flex items-center justify-around px-2
                    lg:hidden z-40 safe-area-bottom">
      {navItems.map(({ icon: Icon, label, href }) => {
        const isActive = location.pathname === href;

        return (
          <NavLink
            key={href}
            to={href}
            className={`flex flex-col items-center justify-center gap-1 px-3 py-2 rounded-lg
                       transition-colors min-w-[64px]
                       ${isActive ? 'text-accent-primary' : 'text-text-tertiary'}`}
          >
            <Icon className="w-5 h-5" />
            <span className="text-[10px] font-medium">{label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
